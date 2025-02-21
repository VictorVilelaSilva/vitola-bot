import discord
import os
from datetime import timedelta

from src.commands.helpers.pathUtils import get_audio_path # Supondo que você criou em outro arquivo

async def silenceMemberFunc(ctx, bot, member: discord.Member):
    if bot.IS_EXECUTING_COMMAND:
        bot.QUEUE.append({"type": "silenceMember", "ctx": ctx, "member": member})
        await ctx.send("Adicionado à fila...")
        return

    bot.IS_EXECUTING_COMMAND = True
    channel = ctx.author.voice.channel
    if channel is not None:
        if bot.vc is None or not bot.vc.is_connected():
            bot.vc = await channel.connect()

        file_path = get_audio_path("silencer_member.mp3")
        if not os.path.isfile(file_path):
            await ctx.send("Arquivo não encontrado!")
            await bot.vc.disconnect()
            return

        bot.vc.play(discord.FFmpegPCMAudio(file_path), after=lambda e: print("done", e))
        await member.edit(mute=True)

        while bot.vc.is_playing():
            await discord.utils.sleep_until(discord.utils.utcnow() + timedelta(seconds=1))

        await member.edit(mute=False)

        bot.IS_EXECUTING_COMMAND = False
        if len(bot.QUEUE):
            await bot.call_next_in_QUEUE()
        else:
            await bot.vc.disconnect()


async def silenceFunc(ctx, bot):
    if bot.IS_EXECUTING_COMMAND:
        bot.QUEUE.append({"type": "silence", "ctx": ctx})
        await ctx.send("Adicionado à fila...")
        return

    bot.IS_EXECUTING_COMMAND = True
    channel = ctx.author.voice.channel
    if channel is not None:
        if bot.vc is None or not bot.vc.is_connected():
            bot.vc = await channel.connect()

        file_path = os.path.join(os.getcwd(), "src/assets/audios/silencer.mp3")
        print(file_path)
        if not os.path.isfile(file_path):
            await ctx.send("Arquivo não encontrado!")
            await bot.vc.disconnect()
            return

        bot.vc.play(discord.FFmpegPCMAudio(file_path), after=lambda e: print("done", e))

        for member in channel.members:
            if member != bot.client.user:
                await member.edit(mute=True)

        await discord.utils.sleep_until(discord.utils.utcnow() + timedelta(seconds=6))

        for member in channel.members:
            await member.edit(mute=False)

        bot.IS_EXECUTING_COMMAND = False
        if len(bot.QUEUE):
            await bot.call_next_in_QUEUE()
        else:
            await bot.vc.disconnect()
