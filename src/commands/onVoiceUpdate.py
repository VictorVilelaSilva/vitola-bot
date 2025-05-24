import os
from datetime import timedelta
import discord
from src.commands.helpers.pathUtils import get_audio_path

async def handle_on_voice_update(bot, member, after):
    audio_map = {
        "humberto_cunha": "lobinho.mp3",
        "gustavotoaiari": "Gustavo.mp3",
        "brunodss": "Bruno.mp3",
        "dino.l": "Dino.mp3",
        "vitolaapenas": "Victor.mp3",
    }
    filename = audio_map.get(member.name)
    if not filename:
        return False

    bot.IS_EXECUTING_COMMAND = True
    if bot.vc is None or not bot.vc.is_connected():
        bot.vc = await after.channel.connect()

    path = get_audio_path(filename)
    print(path)
    if not os.path.isfile(path):
        await bot.send_message_to_chat(bot.client, "Arquivo não encontrado!", bot.CODIGO_CHANNEL_TOKEN)
        await bot.vc.disconnect()
        bot.IS_EXECUTING_COMMAND = False
        return True

    bot.vc.play(discord.FFmpegPCMAudio(path), after=lambda e: print("done", e))
    while bot.vc.is_playing():
        await discord.utils.sleep_until(discord.utils.utcnow() + timedelta(seconds=1))

    await bot.vc.disconnect()
    bot.IS_EXECUTING_COMMAND = False
    return True
