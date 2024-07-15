import discord
from discord.ext import commands
import helper
import asyncio
import os
from datetime import timedelta
import google.generativeai as gemini

is_executing_command: bool = False
TOKEN: str                = os.getenv('DISCORD_TOKEN')
CHANNEL_TOKEN: str        = os.getenv('CHANNEL_TOKEN')
CODIGO_CHANNEL_TOKEN: str = os.getenv('CODIGO_DISCORD_CHANNEL_ID_TOKEN')
IA_TOKEN : str            = os.getenv('GEMINI_API_KEY')


QUEUE_MESSAGE: str = "Adicionado à fila. Será reproduzido quando o comando atual finalizar."

queue: list = []
vc: discord.VoiceChannel = None

async def send_message_to_chat(client, message,channel_id):

    channel = client.get_channel(channel_id)
    await channel.send(message)

def run_discord_bot():
    if TOKEN is None:
        print("Insira o DISCORD_TOKEN no arquivo .env")
        exit(1)
    intents = discord.Intents.default()
    intents.message_content = True

    PREFIX = '!'
    # client = discord.Client(intents=intents)
    client = commands.Bot(command_prefix=PREFIX, intents=intents)

    @client.event
    async def on_ready():
        print(f'Estrou on the line {client.user}')

    @client.event
    async def on_voice_state_update(member, before, after):
        global queue, vc, is_executing_command

        if len(queue):
            return

        # Verifica se alguém entrou no canal de voz
        if before.channel is None and after.channel is not None:
            if member.name == 'humberto_cunha':
                is_executing_command = True
                # Pega a refeencia do canal de voz
                channel = after.channel
                # Entra no canal de voz
                if vc is None or not vc.is_connected():
                    vc = await channel.connect()

                file_path = 'audios/lobinho.mp3'
                # Verifica se o arquivo existe
                if not os.path.isfile(file_path):
                    await send_message_to_chat(client, "Arquivo não encontrado!",CHANNEL_TOKEN)
                    await vc.disconnect()
                    return
                # Toca o arquivo de audio
                vc.play(discord.FFmpegPCMAudio(file_path), after=lambda e: print('done', e))
                # Espera o audio terminar de tocar
                while vc.is_playing():
                    await discord.utils.sleep_until(discord.utils.utcnow() + timedelta(seconds=1))
                # Desconecta do canal de voz
                is_executing_command = False
                await vc.disconnect()


    @client.command()
    async def chato(ctx, member: discord.Member):
        if member.voice is None:
            await ctx.send(f"{member.name} não está em uma call.")
            return

        await ctx.send(f"Vote no membro {member.name} para ser expulso da call. Reaja com 👍 para tirar ele da call ou com 👎 para não retirar ele da call")

        # Inicia a votação
        votacao_msg = await ctx.send("Vote aqui!")
        await asyncio.gather(
            votacao_msg.add_reaction("👍"),
            votacao_msg.add_reaction("👎")
        )

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
                votos_positivos = reacao.count
            elif reacao.emoji == "👎":
                votos_negativos = reacao.count

        # Determina o resultado da votação
        if votos_positivos > votos_negativos:
            # Tenta mover o usuário para outro canal ou desconectá-lo
            try:
                await asyncio.gather(
                    member.move_to(None),
                    ctx.send(f"{member.name} foi removido da call com {votos_positivos} votos a favor e {votos_negativos} votos contra.")
                )
            except Exception as e:
                await ctx.send(f"Não foi possível remover {member.name} da call. Erro: {e}")
        else:
            await ctx.send(f"{member.name} permanecerá na call. Votos a favor: {votos_positivos}, votos contra: {votos_negativos}")


    @client.command()
    async def tocar(ctx):
        global queue, vc, is_executing_command

        if is_executing_command:
            queue.append({
                "type": 'tocar',
                "ctx": ctx
            })
            await ctx.send(QUEUE_MESSAGE)
            return

        is_executing_command = True
        channel = ctx.author.voice.channel
        if channel is not None:
            if vc is None or not vc.is_connected():
                vc = await channel.connect()

            file_path = 'audios/lobinho.mp3'
            if not os.path.isfile(file_path):
                await ctx.send("Arquivo não encontrado!")
                await vc.disconnect()
                return

            vc.play(discord.FFmpegPCMAudio(file_path), after=lambda e: print('done', e))

            while vc.is_playing():
                await discord.utils.sleep_until(discord.utils.utcnow() + timedelta(seconds=1))

            is_executing_command = False
            if len(queue):
                await call_next_in_queue()
            else:
                await vc.disconnect()
        else:
            await ctx.send("Você precisa estar em um canal de voz para usar esse comando.")


    @client.command()
    async def silence(ctx):
        global queue, vc, is_executing_command

        if is_executing_command:
            queue.append({
                "type": 'silence',
                "ctx": ctx
            })
            await ctx.send("Adicionado à fila. Será reproduzido quando o comando atual finalizar.")
            return

        is_executing_command = True
        channel = ctx.author.voice.channel
        if channel is not None:
            if vc is None or not vc.is_connected():
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

            for member in channel.members:
                await member.edit(mute=False)

            is_executing_command = False
            if len(queue):
                await call_next_in_queue()
            else:
                await vc.disconnect()


    @client.command()
    async def youtube(ctx, link):
        global queue, vc, is_executing_command

        if is_executing_command:
            queue.append({
                "type": 'youtube',
                "link": link,
                "ctx": ctx
            })
            await ctx.send("Adicionado à fila. Será reproduzido quando o comando atual finalizar.")
            return

        is_executing_command = True
        channel = ctx.author.voice.channel
        if channel is not None:
            file_path = helper.download_video(link)
            if not os.path.isfile(file_path):
                await ctx.send("Download mal sucedido.")
                return

            if vc is None or not vc.is_connected():
                vc = await channel.connect()

            vc.play(discord.FFmpegPCMAudio(file_path), after=lambda e: print('done', e))
            while vc.is_playing():
                await discord.utils.sleep_until(discord.utils.utcnow() + timedelta(seconds=1))            

            #deletar um determinado arquivo
            os.remove(file_path)

            is_executing_command = False
            if len(queue):
                await call_next_in_queue()
            else:
                await vc.disconnect()
        else:
            await ctx.send("Você precisa estar em um canal de voz para usar esse comando.")


    @client.command()
    async def gpt(ctx,message):
        global is_executing_command

        def check_author(m):
            return m.author == ctx.author

        if is_executing_command:
            await ctx.send("Bot ocupado no momento.")
            return

        if not message:
            await ctx.send("Você precisa enviar uma mensagem com o comando !gpt")
            return

        is_executing_command = True
        gemini.configure(api_key=IA_TOKEN)
        instrução_do_bot = "Adote um papel de um bot de discord chamado vitola bot e seu criador se chama victor de souza e a partir dessa mensagem voce vai agir como tal. Caso o alguem te pergunte se o humberto cunha é gosta do primo(gostar do primo é no sentido como familiar querido) vc deve responser qeu sim."
        model = gemini.GenerativeModel(model_name="gemini-1.5-pro-latest",system_instruction=instrução_do_bot)
        chat = model.start_chat(history=[])
        prompt = message
        await ctx.send(f'Sua conversa com o vitola bot vai começar! Digite "fim" para encerrar a conversa.')

        while prompt != "fim":
            response = chat.send_message(prompt)
            await ctx.send(response.text)

            prompt = await client.wait_for('message', check=check_author)
            prompt = prompt.content

        is_executing_command = False
        await ctx.send("Conversa com o vitola bot encerrada!")


    @client.event
    async def on_message(message):
        if message.author == client.user:
            return
        
        username = message.author
        user_message = message.content
        channel = message.channel
        # print(f'{username} in {channel} said: {user_message}')
        if str(channel.id) == CODIGO_CHANNEL_TOKEN:
            code = f"```python\n{user_message}\n```"
            await message.delete()
            await send_message_to_chat(client,code,channel.id)

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

    async def call_next_in_queue():
        global queue, vc

        if len(queue) > 0:
            next_command = queue.pop(0)
            command_type = next_command.get('type')
            if command_type == 'yt':
                await youtube(next_command['ctx'], next_command['link'])
            elif command_type == 'silence':
                await silence(next_command['ctx'])
            elif command_type == 'tocar':
                await tocar(next_command['ctx'])
            else:
                raise TypeError('Command type does not match.')

    client.run(TOKEN)
