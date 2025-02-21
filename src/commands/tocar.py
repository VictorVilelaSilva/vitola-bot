import discord
import os
from datetime import timedelta


async def tocarFunc(ctx,bot):
    if bot.IS_EXECUTING_COMMAND:
        bot.QUEUE.append({"type": "tocar", "ctx": ctx})
        await ctx.send(
            "Adicionado à fila. Será reproduzido quando o comando atual finalizar."
        )
        return

    bot.IS_EXECUTING_COMMAND = True
    channel = ctx.author.voice.channel
    if channel is not None:
        if bot.vc is None or not bot.vc.is_connected():
            bot.vc = await channel.connect()

        file_path = os.path.join(os.getcwd(), "src/assets/audios/lobinho.mp3")
        if not os.path.isfile(file_path):
            await ctx.send("Arquivo não encontrado!")
            await bot.vc.disconnect()
            return

        bot.vc.play(
            discord.FFmpegPCMAudio(file_path), after=lambda e: print("done", e)
        )

        while bot.vc.is_playing():
            await discord.utils.sleep_until(
                discord.utils.utcnow() + timedelta(seconds=1)
            )

        bot.IS_EXECUTING_COMMAND = False
        if len(bot.QUEUE):
            await bot.call_next_in_QUEUE()
        else:
            await bot.vc.disconnect()
    else:
        await ctx.send(
            "Você precisa estar em um canal de voz para usar esse comando."
        )