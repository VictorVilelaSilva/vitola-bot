import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from src.services.player import AudioTrack, GuildPlayer
from src.services.youtube import (
    DownloadError,
    YouTubeDownloader,
    validate_media_url,
    validate_youtube_url,
)
from src.utils import audio_path, require_voice


class MusicCog(commands.Cog, name="Música"):
    def __init__(self, bot):
        self.bot = bot
        self.players: dict[int, GuildPlayer] = {}
        self.downloader = YouTubeDownloader(bot.settings)

    def get_player(self, guild):
        if guild.id not in self.players:
            self.players[guild.id] = GuildPlayer(guild, self.downloader, self.bot.settings)
        return self.players[guild.id]

    async def cog_check(self, ctx):
        if ctx.guild is None:
            raise commands.NoPrivateMessage()
        return True

    async def cog_unload(self):
        await asyncio.gather(*(player.close() for player in self.players.values()))
        self.players.clear()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        player = self.players.pop(guild.id, None)
        if player:
            await player.close()

    async def enqueue_local(self, ctx, filename, *, effect=None):
        channel = require_voice(ctx)
        track = AudioTrack(
            title=filename,
            channel=channel,
            destination=ctx.channel,
            path=audio_path(filename),
            effect=effect,
        )
        self.get_player(ctx.guild).enqueue(track)
        await ctx.send("Áudio adicionado à fila.")

    @commands.hybrid_command(help="Toca o áudio do lobinho.")
    @commands.cooldown(1, 3, commands.BucketType.member)
    async def tocar(self, ctx):
        await self.enqueue_local(ctx, "lobinho.mp3")

    @commands.hybrid_command(help="Toca o áudio ripita.")
    @commands.cooldown(1, 3, commands.BucketType.member)
    async def ripita(self, ctx):
        await self.enqueue_local(ctx, "ripita.mp3")

    @commands.hybrid_command(help="Toca o áudio autismo.")
    @commands.cooldown(1, 3, commands.BucketType.member)
    async def autismo(self, ctx):
        await self.enqueue_local(ctx, "autismo.mp3")

    @commands.hybrid_command(help="Toca o áudio bahiano.")
    @commands.cooldown(1, 3, commands.BucketType.member)
    async def bahiano(self, ctx):
        await self.enqueue_local(ctx, "bahiano.mp3")

    @commands.hybrid_command(help="Toca o áudio RJ.")
    @commands.cooldown(1, 3, commands.BucketType.member)
    async def rj(self, ctx):
        await self.enqueue_local(ctx, "Rj.mp3")

    @commands.hybrid_command(
        aliases=["yt"], help="Enfileira um vídeo. Use !yt next para pular ou !yt quit para parar."
    )
    @app_commands.describe(link="Link do YouTube, 'next' para pular ou 'quit' para parar")
    @commands.cooldown(1, 3, commands.BucketType.member)
    async def youtube(self, ctx, link: str):
        channel = require_voice(ctx)
        player = self.get_player(ctx.guild)
        player.check_channel(channel)
        if link.lower() == "next":
            skipped = await player.skip()
            await ctx.send("Áudio pulado." if skipped else "Nenhum áudio em reprodução.")
        elif link.lower() == "quit":
            await player.stop()
            await ctx.send("Fila limpa. Saindo do canal de voz.")
        else:
            try:
                url = validate_youtube_url(link)
            except DownloadError as error:
                raise commands.BadArgument(str(error)) from error
            player.enqueue(AudioTrack(title=url, channel=channel, destination=ctx.channel, url=url))
            await ctx.send("Vídeo adicionado à fila.")

    @commands.hybrid_command(
        aliases=["baixarvideo"],
        help="Baixa um vídeo de uma plataforma compatível e envia neste canal.",
    )
    @app_commands.describe(link="Link do vídeo em uma plataforma compatível")
    @commands.cooldown(1, 10, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.member, wait=False)
    async def video(self, ctx, link: str):
        await ctx.defer()
        try:
            url = validate_media_url(link)
        except DownloadError as error:
            raise commands.BadArgument(str(error)) from error

        discord_limit = getattr(ctx.guild, "filesize_limit", self.bot.settings.max_video_bytes)
        max_bytes = min(discord_limit, self.bot.settings.max_video_bytes)
        try:
            async with self.downloader.prepare_video(url, max_bytes) as downloaded:
                attachment = discord.File(downloaded.path, filename=downloaded.path.name)
                try:
                    await ctx.send(f"Vídeo baixado: {downloaded.title[:180]}", file=attachment)
                finally:
                    attachment.close()
        except DownloadError as error:
            raise commands.CheckFailure(str(error)) from error

    @commands.hybrid_command(
        help="Extrai o áudio de um vídeo compatível e envia em MP3.",
    )
    @app_commands.describe(link="Link do vídeo em uma plataforma compatível")
    @commands.cooldown(1, 10, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.member, wait=False)
    async def mp3(self, ctx, link: str):
        await ctx.defer()
        try:
            url = validate_media_url(link)
        except DownloadError as error:
            raise commands.BadArgument(str(error)) from error

        discord_limit = getattr(ctx.guild, "filesize_limit", self.bot.settings.max_download_bytes)
        max_bytes = min(discord_limit, self.bot.settings.max_download_bytes)
        try:
            async with self.downloader.prepare_mp3(url, max_bytes) as downloaded:
                attachment = discord.File(downloaded.path, filename="audio.mp3")
                try:
                    await ctx.send(f"MP3 extraído: {downloaded.title[:180]}", file=attachment)
                finally:
                    attachment.close()
        except DownloadError as error:
            raise commands.CheckFailure(str(error)) from error

    @commands.hybrid_command(
        name="fila",
        aliases=["showQueue"],
        help="Mostra o áudio atual e os próximos itens deste servidor.",
    )
    @commands.cooldown(1, 3, commands.BucketType.member)
    async def show_queue(self, ctx):
        player = self.get_player(ctx.guild)
        embed = discord.Embed(title="Fila de reprodução", color=discord.Color.red())
        if player.current:
            embed.description = f"Tocando/preparando: {player.current.title[:200]}"
        if not player.pending:
            embed.add_field(name="Próximos", value="Nenhum áudio na fila.", inline=False)
        for index, track in enumerate(player.pending[:20], 1):
            embed.add_field(
                name=f"{index}. {track.title[:180]}", value=track.url or "Áudio local", inline=False
            )
        if len(player.pending) > 20:
            embed.set_footer(text=f"Mais {len(player.pending) - 20} itens na fila.")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(MusicCog(bot))
