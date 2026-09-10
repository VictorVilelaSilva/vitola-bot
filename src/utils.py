from pathlib import Path

import discord
from discord.ext import commands

ASSETS_DIR = Path(__file__).resolve().parent / "assets" / "audios"


def audio_path(filename: str) -> Path:
    path = ASSETS_DIR / filename
    if path.parent != ASSETS_DIR or not path.is_file():
        raise commands.CheckFailure("Arquivo de áudio não encontrado.")
    return path


def require_voice(ctx, *permissions):
    if ctx.guild is None:
        raise commands.NoPrivateMessage()
    if not ctx.author.voice or not ctx.author.voice.channel:
        raise commands.CheckFailure("Você precisa estar em um canal de voz.")
    channel = ctx.author.voice.channel
    if not isinstance(channel, discord.VoiceChannel):
        raise commands.CheckFailure("Use um canal de voz comum; palcos não são suportados.")
    bot_permissions = channel.permissions_for(ctx.guild.me)
    missing = [
        name for name in ("connect", "speak", *permissions) if not getattr(bot_permissions, name)
    ]
    if missing:
        raise commands.BotMissingPermissions(missing)
    author_permissions = channel.permissions_for(ctx.author)
    missing = [name for name in permissions if not getattr(author_permissions, name)]
    if missing:
        raise commands.MissingPermissions(missing)
    return channel


async def send_text(destination, text: str):
    for start in range(0, len(text), 1900):
        await destination.send(
            text[start : start + 1900], allowed_mentions=discord.AllowedMentions.none()
        )
