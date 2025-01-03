# commands/youtube.py

import os
import discord
import commands.helpers.helper as helper
from commands.helpers.EmbedMessages import ytEmbed
from datetime import timedelta

async def youtubeFunc(ctx, link, bot):
    if bot.IS_EXECUTING_COMMAND:
        if link == 'next':
            bot.vc.stop()
            await bot.call_next_in_QUEUE()
            return
        elif link == 'quit':
            bot.vc.stop()
            await bot.vc.disconnect()
            bot.QUEUE = []
            await ctx.send('Saindo do canal de voz.')
            return
        else:
            bot.QUEUE.append({"type": "youtube", "link": link, "ctx": ctx, "title": helper.get_yt_title(link), "thumbnail": helper.get_yt_thumbnail(link)})
            await ctx.send(
                "Adicionado à fila. Será reproduzido quando o comando atual finalizar."
            )
            return

    bot.IS_EXECUTING_COMMAND = True
    channel = ctx.author.voice.channel
    if channel is not None:
        file_path, yt_title,thumbnail = helper.download_video(link)
        if not os.path.isfile(file_path):
            await ctx.send("Download mal sucedido.")
            return
        
        if bot.vc is None or not bot.vc.is_connected():
            bot.vc = await channel.connect()

        await ctx.send(embed=ytEmbed(yt_title, link, thumbnail))

        bot.vc.play(
            discord.FFmpegPCMAudio(file_path), after=lambda e: print("done", e)
        )
        while bot.vc.is_playing():
            await discord.utils.sleep_until(
                discord.utils.utcnow() + timedelta(seconds=1)
            )

        os.remove(file_path)

        bot.IS_EXECUTING_COMMAND = False
        if len(bot.QUEUE):
            await bot.call_next_in_QUEUE()
        else:
            await bot.vc.disconnect()
    else:
        await ctx.send(
            "Você precisa estar em um canal de voz para usar esse comando."
        )
