import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from discord.ext import commands

from src.config import Settings
from src.services.player import AudioTrack, GuildPlayer
from src.services.youtube import DownloadedAudio, DownloadError
from tests.conftest import FakeSource, FakeVoice, wait_until


@pytest.fixture
def player(context, monkeypatch, tmp_path):
    audio = tmp_path / "audio.webm"
    audio.write_bytes(b"audio")

    @asynccontextmanager
    async def prepare(url):
        if url == "bad":
            raise DownloadError("Download indisponível.")
        yield DownloadedAudio(path=audio, title="YouTube title")

    voice = FakeVoice(context.voice_channel)
    context.guild.voice_client = voice

    async def connect(**kwargs):
        voice.connected = True
        context.guild.voice_client = voice
        return voice

    context.voice_channel.connect.side_effect = connect
    monkeypatch.setattr("src.services.player.discord.FFmpegPCMAudio", FakeSource)
    return GuildPlayer(context.guild, SimpleNamespace(prepare=prepare), Settings()), audio, voice


async def test_mixed_queue_continues_after_download_failure(player, context):
    instance, audio, voice = player
    effect_entered = []

    @asynccontextmanager
    async def effect():
        effect_entered.append("enter")
        try:
            yield
        finally:
            effect_entered.append("exit")

    try:
        for track in (
            AudioTrack("local", context.voice_channel, path=audio),
            AudioTrack("bad", context.voice_channel, context.channel, url="bad"),
            AudioTrack("youtube", context.voice_channel, url="good"),
            AudioTrack("silence", context.voice_channel, path=audio, effect=effect),
        ):
            instance.enqueue(track)
        await asyncio.wait_for(instance.queue.join(), 2)
        assert len(voice.played) == 3
        assert effect_entered == ["enter", "exit"]
        assert instance.pending == []
        assert instance.current is None
        assert context.channel.send.await_args.args[0] == "Download indisponível."
        assert not instance._worker.done()
    finally:
        await instance.close()


async def test_skip_empty_and_last_track_are_safe(player, context):
    instance, audio, voice = player
    voice.auto_finish = False
    try:
        assert await instance.skip() is False
        instance.enqueue(AudioTrack("local", context.voice_channel, path=audio))
        await voice.started.wait()
        assert await instance.skip() is True
        await asyncio.wait_for(instance.queue.join(), 2)
        assert await instance.skip() is False
        assert not instance._worker.done()
    finally:
        await instance.close()


async def test_local_audio_does_not_announce_internal_filename(player, context):
    instance, audio, _ = player
    try:
        instance.enqueue(
            AudioTrack(
                "silencer.mp3",
                context.voice_channel,
                destination=context.channel,
                path=audio,
            )
        )
        await asyncio.wait_for(instance.queue.join(), 2)
        context.channel.send.assert_not_called()
    finally:
        await instance.close()


async def test_youtube_audio_announces_downloaded_title(player, context):
    instance, _, _ = player
    try:
        instance.enqueue(
            AudioTrack(
                "https://www.youtube.com/watch?v=abcdefghijk",
                context.voice_channel,
                destination=context.channel,
                url="good",
            )
        )
        await asyncio.wait_for(instance.queue.join(), 2)
        assert context.channel.send.await_args.args[0] == "Tocando: YouTube title"
    finally:
        await instance.close()


async def test_stop_clears_pending_and_runs_effect_cleanup(player, context):
    instance, audio, voice = player
    voice.auto_finish = False
    restored = asyncio.Event()

    @asynccontextmanager
    async def effect():
        try:
            yield
        finally:
            restored.set()

    try:
        instance.enqueue(AudioTrack("mute", context.voice_channel, path=audio, effect=effect))
        instance.enqueue(AudioTrack("pending", context.voice_channel, path=audio))
        await voice.started.wait()
        await instance.stop()
        await asyncio.wait_for(instance.queue.join(), 2)
        assert restored.is_set()
        assert instance.pending == []
        assert instance.channel_id is None
        assert context.guild.voice_client is None
        assert len(voice.played) == 1
    finally:
        await instance.close()


async def test_queue_and_channel_limits(player, context):
    instance, audio, _ = player
    instance.settings = Settings(queue_size=1)
    instance.queue = asyncio.Queue(maxsize=1)
    try:
        instance.enqueue(AudioTrack("one", context.voice_channel, path=audio))
        with pytest.raises(commands.CheckFailure, match="cheia"):
            instance.enqueue(AudioTrack("two", context.voice_channel, path=audio))
        other = SimpleNamespace(id=99, guild=context.guild)
        with pytest.raises(commands.CheckFailure, match="outro canal"):
            instance.enqueue(AudioTrack("other", other, path=audio))
    finally:
        await instance.close()


async def test_players_in_two_guilds_run_independently(player, context):
    first, audio, voice = player
    voice.auto_finish = False
    second_guild = SimpleNamespace(id=2, voice_client=None, me=context.guild.me)
    second_channel = SimpleNamespace(
        id=30,
        guild=second_guild,
        permissions_for=context.voice_channel.permissions_for,
    )
    second_voice = FakeVoice(second_channel, auto_finish=False)
    second_guild.voice_client = second_voice
    second = GuildPlayer(second_guild, first.downloader, Settings())
    try:
        first.enqueue(AudioTrack("one", context.voice_channel, path=audio))
        second.enqueue(AudioTrack("two", second_channel, path=audio))
        await asyncio.wait_for(asyncio.gather(voice.started.wait(), second_voice.started.wait()), 2)
        await first.stop()
        assert second.current is not None
        assert second_voice.connected
    finally:
        await first.close()
        await second.close()


async def test_stop_during_preparation_allows_new_track(player, context):
    instance, audio, voice = player
    started, cleaned = asyncio.Event(), asyncio.Event()

    @asynccontextmanager
    async def slow_download(url):
        started.set()
        try:
            await asyncio.Event().wait()
            yield
        finally:
            cleaned.set()

    instance.downloader.prepare = slow_download
    try:
        instance.enqueue(AudioTrack("slow", context.voice_channel, url="slow"))
        await started.wait()
        await instance.stop()
        assert cleaned.is_set()
        context.guild.voice_client = voice
        instance.enqueue(AudioTrack("local", context.voice_channel, path=audio))
        await asyncio.wait_for(instance.queue.join(), 2)
        assert voice.played == [str(audio)]
    finally:
        await instance.close()


async def test_stop_immediately_after_enqueue_does_not_kill_worker(player, context):
    instance, audio, voice = player
    try:
        instance.enqueue(AudioTrack("cancelled", context.voice_channel, path=audio))
        await instance.stop()
        context.guild.voice_client = voice
        voice.connected = True
        instance.enqueue(AudioTrack("next", context.voice_channel, path=audio))
        await asyncio.wait_for(instance.queue.join(), 2)
        assert len(voice.played) == 1
        await wait_until(lambda: instance.current is None)
        assert not instance._worker.done()
    finally:
        await instance.close()


async def test_close_before_worker_starts_disconnects_existing_voice(player, context):
    instance, audio, voice = player
    instance.enqueue(AudioTrack("local", context.voice_channel, path=audio))
    await instance.close()
    assert not voice.connected
    assert context.guild.voice_client is None


async def test_cancel_during_connection_cleans_partial_voice_client(player, context):
    instance, audio, voice = player
    context.guild.voice_client = None
    started = asyncio.Event()

    async def connect(**kwargs):
        context.guild.voice_client = voice
        started.set()
        await asyncio.Event().wait()

    context.voice_channel.connect.side_effect = connect
    try:
        instance.enqueue(AudioTrack("local", context.voice_channel, path=audio))
        await started.wait()
        await instance.skip()
        await asyncio.wait_for(instance.queue.join(), 2)
        assert context.guild.voice_client is None
        assert not voice.connected
    finally:
        await instance.close()
