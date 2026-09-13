import logging
from types import SimpleNamespace
from typing import ClassVar

import discord
from discord.ext import commands

from src.services.player import AudioTrack
from src.utils import audio_path

log = logging.getLogger(__name__)


class CommunityCog(commands.Cog, name="Comunidade"):
    # Preserve the existing server's greetings; these can be replaced by member IDs.
    ENTRY_AUDIO: ClassVar[dict[str, str]] = {
        "humberto_cunha": "lobinho.mp3",
        "gustavotoaiari": "Gustavo.mp3",
        "brunodss": "Bruno.mp3",
        "dino.l": "Dino.mp3",
        "modesto1": "Edvaldo.mp3",
    }

    def __init__(self, bot):
        self.bot = bot
        self._entry_cooldown = commands.CooldownMapping.from_cooldown(
            1, 30, commands.BucketType.member
        )

    # @commands.Cog.listener()
    # async def on_voice_state_update(self, member, before, after):
    #     if (
    #         member.bot
    #         or before.channel is not None
    #         or not isinstance(after.channel, discord.VoiceChannel)
    #     ):
    #         return
    #     filename = self.ENTRY_AUDIO.get(member.name)
    #     music = self.bot.get_cog("Música")
    #     if not filename or music is None:
    #         return
    #     # CooldownMapping's member bucket expects a message-like author/guild.
    #     bucket = self._entry_cooldown.get_bucket(SimpleNamespace(author=member, guild=member.guild))
    #     if bucket.update_rate_limit():
    #         return
    #     try:
    #         music.get_player(member.guild).enqueue(
    #             AudioTrack(title=filename, channel=after.channel, path=audio_path(filename)),
    #         )
    #     except commands.CheckFailure:
    #         log.info("Áudio de entrada ignorado: canal ocupado, fila cheia ou arquivo ausente.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.guild is None:
            return
        # Commands are processed by Bot.on_message; this listener handles only community features.
        if message.content.startswith("!"):
            return
        try:
            if message.channel.id == self.bot.settings.code_channel_id:
                formatted = "\x60\x60\x60python\n" + message.content + "\n\x60\x60\x60"
                if message.content and len(formatted) <= 2000 and not message.attachments:
                    await message.channel.send(
                        formatted, allowed_mentions=discord.AllowedMentions.none()
                    )
                    await message.delete()
            if message.author.name == "chaul0205":
                await message.add_reaction("<:Chaul:1243037858907029534>")
            elif message.author.name == "humberto_cunha":
                await message.add_reaction("🐺")
            elif message.author.name == "brunodss":
                await message.reply("Você é PUTA RAPAZ!", mention_author=False)
        except discord.HTTPException:
            log.warning("Não foi possível aplicar a automação à mensagem %s", message.id)


async def setup(bot):
    await bot.add_cog(CommunityCog(bot))
