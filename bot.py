import discord
from discord.ext import commands
from dotenv import load_dotenv
import comandsFunctions
import asyncio
import os
from datetime import timedelta


async def send_message_to_chat(client, message):
    # Obter o objeto channel
    channel = client.get_channel('576190309688672257')

    # Enviar a mensagem
    await channel.send(message)



def run_discord_bot():
    load_dotenv()
    TOKEN = os.getenv('DISCORD_TOKEN')

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
        if before.channel is None and after.channel is not None:
            if member.name == 'humberto_cunha':
                channel = after.channel
                vc = await channel.connect()
                file_path = 'audios/lobinho.mp3'

                if not os.path.isfile(file_path):
                    await send_message_to_chat(client, "Arquivo não encontrado!")
                    await vc.disconnect()
                    return
                
                vc.play(discord.FFmpegPCMAudio(file_path), after=lambda e: print('done', e))

                while vc.is_playing():

                    await discord.utils.sleep_until(discord.utils.utcnow() + timedelta(seconds=1))

                await vc.disconnect()

            else:
                await send_message_to_chat("Você precisa estar em um canal de voz para usar esse comando.")
                    
            print(f'{member.name} se conectou ao canal de voz: {after.channel.name}')
    
    @client.command()
    async def chato(ctx):
        if ctx.guild is None:
            await ctx.send("Esse comando só pode ser usado em servidores.")
            return

        # Verifica se o autor da mensagem tem permissão para mover membros
        if not ctx.author.guild_permissions.move_members:
            await ctx.send("Voce não tem permissão para usar esse comando.")
            return

        # Pegar o primeiro membro mencionado na mensagem
        if len(ctx.message.mentions) == 0:
            await ctx.send("Mencione um usuário para ser chutado.")
            return
        user = ctx.message.mentions[0]

        # Inicia a votação
        await ctx.send(f"Vote no membro {user.mention} para ser chutado. Reaja com 👍 para votar.")

        # adicion uma reção na mensagem digita da pelo bot
        await ctx.message.add_reaction("👍")

        # verifica se a reação é correta
        def check(reaction, user):
            return str(reaction.emoji) == "👍" and reaction.message == ctx.message

        # Espera por reações por 60 segundos
        try:
            reaction, _ = await client.wait_for("reaction_add", timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send("Votação encerrada. Não houve votos suficientes para chutar.")
            return

        # Check if there are enough votes to kick
        if reaction.count > 2:
            # Move o usuario marcado para para fora do nacal de voz
            member = ctx.guild.get_member(user.id)
            await member.move_to(None)
        else:
            await ctx.send("Não houve votos dropar do canal")
    
    @client.command()
    async def tocar(ctx):
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
        
        if username == 'brunodss':
            await message.reply('Você é PUTA RAPAZ!')
        
        await client.process_commands(message)
            # await send_message(message, f'{message.author.mention} <:astral:858408913317134336>', False)
        #     for voice_channel in message.guild.voice_channels:
        #         for member in voice_channel.members:
        #             if member.name == 'vitolaapenas':
        #                 await message.channel.send(':astral: @vitolaapenas :astral:')
        #                 await member.move_to(None)
        #                 break

    client.run(TOKEN)
