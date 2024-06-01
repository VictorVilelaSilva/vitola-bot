import discord
from discord.ext import commands
from dotenv import load_dotenv
import comandsFunctions
import asyncio
import os
from datetime import timedelta

is_executing_command = False

async def send_message_to_chat(client, message):
    # Obter o objeto channel
    channel = client.get_channel('576190309688672257')

    # Enviar a mensagem
    await channel.send(message)


def run_discord_bot():
    load_dotenv()
    TOKEN: str = os.getenv('DISCORD_TOKEN')
    if TOKEN is None:
        print("Insira o DISCORD_TOKEN no arquivo .env")
        exit(1)
    intents = discord.Intents.default()
    intents.message_content = True

    PREFIX = '!'
    # client = discord.Client(intents=intents)
    client = commands.Bot(command_prefix = PREFIX, intents=intents)

    @client.event
    async def on_ready():
        print(f'Estrou on the line {client.user}')

    @client.event
    async def on_voice_state_update(member, before, after):
        global is_executing_command
        if is_executing_command:
            return
        # Verifica se alguém entrou no canal de voz
        if before.channel is None and after.channel is not None:
            if member.name == 'humberto_cunha':
                # Pega a refeencia do canal de voz
                channel = after.channel
                # Entra no canal de voz
                vc = await channel.connect()
                file_path = 'audios/lobinho.mp3'
                # Verifica se o arquivo existe
                if not os.path.isfile(file_path):
                    await send_message_to_chat(client, "Arquivo não encontrado!")
                    await vc.disconnect()
                    return
                # Toca o arquivo de audio
                vc.play(discord.FFmpegPCMAudio(file_path), after=lambda e: print('done', e))
                # Espera o audio terminar de tocar
                while vc.is_playing():
                    await discord.utils.sleep_until(discord.utils.utcnow() + timedelta(seconds=1))
                # Desconecta do canal de voz
                await vc.disconnect()


    @client.command()
    async def chato(ctx, member: discord.Member):
        if member.voice is None:
            await ctx.send(f"{member.name} não está em uma call.")
            return

        # Inicia a votação
        await ctx.send(f"Vote no membro {member.name} para ser expulso da call. Reaja com 👍 para tirar ele da call ou com 👎 para não retirar ele da call")

        # Envia a mensagem de votação
        votacao_msg = await ctx.send("Vote agora aqui !")
        await votacao_msg.add_reaction("👍")
        await votacao_msg.add_reaction("👎")

        # Tempo de votação (em segundos)
        tempo_votacao = 6

        await asyncio.sleep(tempo_votacao)
        await ctx.send("Votação encerrada!")

        # Atualiza a mensagem para obter as reações mais recentes
        votacao_msg = await ctx.fetch_message(votacao_msg.id)

        # Conta as reações
        reacoes = votacao_msg.reactions
        votos_positivos = 0
        votos_negativos = 0

        for reacao in reacoes:
            if reacao.emoji == "👍":
                votos_positivos = reacao.count - 1  # Subtrai 1 para não contar o voto do próprio bot
            elif reacao.emoji == "👎":
                votos_negativos = reacao.count - 1  # Subtrai 1 para não contar o voto do próprio bot

        # Determina o resultado da votação
        if votos_positivos > votos_negativos:
            # Tenta mover o usuário para outro canal ou desconectá-lo
            try:
                await member.move_to(None)
                await ctx.send(f"{member.name} foi removido da call com {votos_positivos} votos a favor e {votos_negativos} votos contra.")
            except Exception as e:
                await ctx.send(f"Não foi possível remover {member.name} da call. Erro: {e}")
        else:
            await ctx.send(f"{member.name} permanecerá na call. Votos a favor: {votos_positivos}, votos contra: {votos_negativos}")


    @client.command()
    async def tocar(ctx):
        global is_executing_command

        if is_executing_command:
            await ctx.send("Já estou tocando um áudio!")
            return
        is_executing_command = True
        #entra no canal de voz e toca uma audio
        channel = ctx.author.voice.channel
        if channel is not None:
            vc = await channel.connect()
            file_path = 'audios/lobinho.mp3'

            if not os.path.isfile(file_path):
                await ctx.send("Arquivo não encontrado!")
                await vc.disconnect()
                return

            vc.play(discord.FFmpegPCMAudio(file_path), after=lambda e: print('done', e))

            while vc.is_playing():
                await discord.utils.sleep_until(discord.utils.utcnow() + timedelta(seconds=1))

            await vc.disconnect()
            is_executing_command = False
        else:
            await ctx.send("Você precisa estar em um canal de voz para usar esse comando.")


    @client.command()
    async def silence(ctx):
        global is_executing_command

        if is_executing_command:
            await ctx.send("Já estou tocando um áudio!")
            return

        is_executing_command = True

        channel = ctx.author.voice.channel

        if channel is not None:
            vc = await channel.connect()
            file_path = 'audios/silencer.mp3'

            if not os.path.isfile(file_path):
                await ctx.send("Arquivo não encontrado!")
                await vc.disconnect()
                return

            vc.play(discord.FFmpegPCMAudio(file_path), after=lambda e: print('done', e))

            for member in channel.members:
                if member != client.user: 
                    await member.edit(mute=True)

            while vc.is_playing():
                await discord.utils.sleep_until(discord.utils.utcnow() + timedelta(seconds=1))

            await vc.disconnect()
            is_executing_command = False

            for member in channel.members:
                await member.edit(mute=False)


    @client.command()
    async def youtube(ctx,link):
        global is_executing_command

        if is_executing_command:
            await ctx.send("Já estou tocando um áudio!")
            return
        is_executing_command = True
        channel = ctx.author.voice.channel

        if channel is not None:
            await ctx.send("Aguarde um momento...")
            file_path = comandsFunctions.dowloadVideo(link)
            await ctx.send("Download concluído!")
            vc = await channel.connect()
            if not os.path.isfile(file_path):
                await ctx.send("Arquivo não encontrado!")
                await vc.disconnect()
                return
            vc.play(discord.FFmpegPCMAudio(file_path), after=lambda e: print('done', e))
            while vc.is_playing():
                await discord.utils.sleep_until(discord.utils.utcnow() + timedelta(seconds=1))

            await vc.disconnect()
            is_executing_command = False

            #deletar um determinado arquivo
            os.remove(file_path)
        else:
            await ctx.send("Você precisa estar em um canal de voz para usar esse comando.")


    @client.event
    async def on_message(message):
        if message.author == client.user:
            return

        username = str(message.author)
        user_message = str(message.content)
        channel = str(message.channel)
        print(f'{username} in {channel} said: {user_message}')

        if username == 'chaul0205':
            await message.add_reaction('<:Chaul:1243037858907029534>')
        if username == 'humberto_cunha':
            await message.add_reaction('🐺')
        if username == 'brunodss':
            await message.reply('Você é PUTA RAPAZ!')

        await client.process_commands(message)
        # await send_message(message, f'{message.author.mention} <:astral:858408913317134336>', False)
        # for voice_channel in message.guild.voice_channels:
        #     for member in voice_channel.members:
        #         if member.name == 'vitolaapenas':
        #             await message.channel.send(':astral: @vitolaapenas :astral:')
        #             await member.move_to(None)
        #             break

    client.run(TOKEN)
