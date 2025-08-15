import os
import asyncio
import discord
from src.commands.helpers.pathUtils import get_audio_path


async def play_audio(ctx, bot, audio_file: str) -> None:
    """
    Reproduz um arquivo de áudio no canal de voz do Discord.
    Versão simplificada baseada no importos.py que funciona corretamente.
    """
    # Verifica se o usuário está em um canal de voz
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("Você precisa estar em um canal de voz para usar esse comando.")
        return
    
    channel = ctx.author.voice.channel
    
    # Verifica se já está executando um comando
    if getattr(bot, "IS_EXECUTING_COMMAND", False):
        if hasattr(bot, "QUEUE"):
            bot.QUEUE.append({"type": "audio", "ctx": ctx, "audio_file": audio_file})
            await ctx.send("Adicionado à fila. Será reproduzido quando o comando atual finalizar.")
        return
    
    bot.IS_EXECUTING_COMMAND = True
    
    try:
        if not ctx.voice_client:
            voice_client = await channel.connect()
        else:
            voice_client = ctx.voice_client
            if voice_client.channel != channel:
                await voice_client.move_to(channel)
        
        if voice_client.is_playing():
            voice_client.stop()
        
        audio_path = get_audio_path(audio_file)
        
        if not os.path.exists(audio_path):
            await ctx.send("Arquivo de áudio não encontrado!")
            return
        
        voice_client.play(discord.FFmpegPCMAudio(audio_path))
        
        while voice_client.is_playing():
            await asyncio.sleep(0.5)
        
    except Exception as e:
        await ctx.send(f"Erro ao tocar o áudio: {str(e)}")
    finally:
        bot.IS_EXECUTING_COMMAND = False
        
        # Processa próximo item da fila ou desconecta
        if hasattr(bot, "QUEUE") and len(bot.QUEUE) > 0:
            await bot.call_next_in_QUEUE()
        else:
            if ctx.voice_client and ctx.voice_client.is_connected():
                await ctx.voice_client.disconnect()
