import asyncio
import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager, suppress
from dataclasses import dataclass
from pathlib import Path

import discord
from discord.ext import commands

from src.config import Settings
from src.services.youtube import DownloadError, YouTubeDownloader

log = logging.getLogger(__name__)


@dataclass(eq=False)
class AudioTrack:
    title: str
    channel: discord.VoiceChannel
    destination: discord.abc.Messageable | None = None
    path: Path | None = None
    url: str | None = None
    effect: Callable[[], AbstractAsyncContextManager] | None = None


@asynccontextmanager
async def no_effect():
    yield


class GuildPlayer:
    """One consumer owns voice playback and cleanup for one guild."""

    def __init__(self, guild, downloader: YouTubeDownloader, settings: Settings):
        self.guild = guild
        self.downloader = downloader
        self.settings = settings
        self.queue: asyncio.Queue[AudioTrack] = asyncio.Queue(maxsize=settings.queue_size)
        self.pending: list[AudioTrack] = []
        self.current: AudioTrack | None = None
        self.channel_id: int | None = None
        self._worker: asyncio.Task | None = None
        self._play_task: asyncio.Task | None = None
        self._closed = False
        self._stopping = False
        self._controls = asyncio.Lock()
        self._connection = asyncio.Lock()

    def check_channel(self, channel):
        if self.channel_id is not None and self.channel_id != channel.id:
            raise commands.CheckFailure("O bot está atendendo outro canal de voz neste servidor.")

    def enqueue(self, track: AudioTrack):
        if self._closed or self._stopping:
            raise commands.CheckFailure("O player está encerrando. Tente novamente em instantes.")
        if track.channel.guild.id != self.guild.id:
            raise commands.CheckFailure("O áudio pertence a outro servidor.")
        self.check_channel(track.channel)
        if self.queue.full():
            raise commands.CheckFailure(
                f"A fila está cheia (máximo de {self.settings.queue_size} itens)."
            )
        self.channel_id = track.channel.id
        self.queue.put_nowait(track)
        self.pending.append(track)
        if self._worker is None or self._worker.done():
            self._worker = asyncio.create_task(self._run(), name=f"audio-worker-{self.guild.id}")

    async def _notify(self, track, message):
        if track.destination is not None:
            try:
                await track.destination.send(
                    message, allowed_mentions=discord.AllowedMentions.none()
                )
            except discord.HTTPException:
                log.warning(
                    "Não foi possível informar o canal sobre o áudio no servidor %s", self.guild.id
                )

    async def _run(self):
        try:
            while not self._closed:
                try:
                    async with asyncio.timeout(60):
                        track = await self.queue.get()
                except TimeoutError:
                    await self._disconnect()
                    if self.queue.empty():
                        self.channel_id = None
                    continue
                self.pending.remove(track)
                self.current = track
                self._play_task = asyncio.create_task(self._play(track))
                try:
                    await self._play_task
                except asyncio.CancelledError:
                    if self._closed or asyncio.current_task().cancelling():
                        raise
                    # Skip/stop cancelled only this track. Keep the consumer alive.
                except Exception as error:
                    log.exception("Falha ao reproduzir áudio no servidor %s", self.guild.id)
                    message = (
                        str(error)
                        if isinstance(error, (DownloadError, commands.CheckFailure))
                        else "Não consegui reproduzir esse áudio."
                    )
                    await self._notify(track, message)
                finally:
                    self._play_task = None
                    self.current = None
                    self.queue.task_done()
        finally:
            await self._disconnect()

    async def _connect(self, channel):
        async with self._connection:
            permissions = channel.permissions_for(self.guild.me)
            if not permissions.connect or not permissions.speak:
                raise commands.CheckFailure(
                    "Estou sem permissão para conectar ou falar nesse canal."
                )
            voice = self.guild.voice_client
            if voice and voice.is_connected():
                if voice.channel.id != channel.id:
                    await voice.move_to(channel)
                return voice
            if voice:
                await voice.disconnect(force=True)
            return await channel.connect(timeout=20, reconnect=True)

    async def _disconnect(self):
        async with self._connection:
            voice = self.guild.voice_client
            if voice:
                try:
                    await voice.disconnect(force=True)
                except discord.DiscordException:
                    log.exception("Falha ao desconectar voz no servidor %s", self.guild.id)

    async def _play(self, track: AudioTrack):
        if track.url:
            async with self.downloader.prepare(track.url) as audio:
                track.title = audio.title
                await self._play_file(track, audio.path)
        elif track.path:
            await self._play_file(track, track.path)
        else:
            raise commands.CheckFailure("O item da fila não contém áudio.")

    async def _play_file(self, track, path):
        if not path.is_file():
            raise commands.CheckFailure("Arquivo de áudio não encontrado.")
        try:
            voice = await self._connect(track.channel)
        except (Exception, asyncio.CancelledError):
            await self._disconnect()
            raise
        source = discord.FFmpegPCMAudio(str(path), options="-vn")
        loop = asyncio.get_running_loop()
        finished = loop.create_future()

        def complete(error):
            if not finished.done():
                if error:
                    finished.set_exception(error)
                else:
                    finished.set_result(None)

        def after(error):
            loop.call_soon_threadsafe(complete, error)

        try:
            async with track.effect() if track.effect else no_effect():
                try:
                    voice.play(source, after=after)
                    if track.url:
                        await self._notify(track, f"Tocando: {track.title[:200]}")
                    async with asyncio.timeout(self.settings.max_audio_seconds + 30):
                        while not finished.done():
                            try:
                                await asyncio.wait_for(asyncio.shield(finished), timeout=1)
                            except TimeoutError:
                                if not voice.is_connected():
                                    raise commands.CheckFailure(
                                        "A conexão de voz foi interrompida."
                                    )
                        await finished
                finally:
                    voice.stop()
        finally:
            finished.cancel()
            voice.stop()
            source.cleanup()

    async def skip(self) -> bool:
        async with self._controls:
            task = self._play_task
            if task is None or task.done():
                return False
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            return True

    def _clear_queue(self):
        while not self.queue.empty():
            self.queue.get_nowait()
            self.queue.task_done()
        self.pending.clear()

    async def stop(self):
        async with self._controls:
            self._stopping = True
            try:
                self._clear_queue()
                task = self._play_task
                if task and not task.done():
                    task.cancel()
                    with suppress(asyncio.CancelledError):
                        await task
                await self._disconnect()
                self.channel_id = None
            finally:
                self._stopping = False

    async def close(self):
        async with self._controls:
            self._closed = True
            self._clear_queue()
            if self._worker:
                self._worker.cancel()
                with suppress(asyncio.CancelledError):
                    await self._worker
            await self._disconnect()
