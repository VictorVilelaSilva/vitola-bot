from commands import youtubeFunc, silenceFunc, tocarFunc
from EmbedMessages import showYtQueue
from discord.ext import commands
from datetime import timedelta
from Gemini import Gemini
import asyncio
import discord
import glob
import os


from commands.silence import silenceMemberFunc
from helper import write_error_log


class DiscordBot:
    def __init__(self):
        self.client = None
        self.QUEUE: list = []
        self.vc: discord.VoiceChannel = None
        self.IS_EXECUTING_COMMAND: bool = False
        self.CHANNEL_TOKEN = os.getenv("CHANNEL_TOKEN")
        self.TOKEN = os.getenv("DISCORD_TOKEN")
        self.CODIGO_CHANNEL_TOKEN = os.getenv("CODIGO_DISCORD_CHANNEL_ID_TOKEN")
        self.QUEUE_MESSAGE = (
            "Adicionado à fila. Será reproduzido quando a musica atual finalizar."
        )

    async def send_message_to_chat(self, client, message, channel_id):
        channel = client.get_channel(channel_id)
        await channel.send(message)

    def run_discord_bot(self):
        if self.TOKEN is None:
            print("Insira o DISCORD_TOKEN no arquivo .env")
            exit(1)
        intents = discord.Intents.default()
        intents.message_content = True
        self.client = commands.Bot(command_prefix="!", intents=intents)

        @self.client.event
        async def on_ready():
            print(f"Estrou on the line {self.client.user}")

        @self.client.event
        async def on_voice_state_update(member, before, after):
            if len(self.QUEUE):
                return
            if before.channel is None and after.channel is not None:
                if member.name == "humberto_cunha":
                    self.IS_EXECUTING_COMMAND = True
                    channel = after.channel
                    if self.vc is None or not self.vc.is_connected():
                        self.vc = await channel.connect()

                    file_path = "assets/audios/lobinho.mp3"
                    if not os.path.isfile(file_path):
                        await self.send_message_to_chat(
                            self.client, "Arquivo não encontrado!", self.CODIGO_CHANNEL_TOKEN
                        )
                        await self.vc.disconnect()
                        return

                    self.vc.play(
                        discord.FFmpegPCMAudio(file_path),
                        after=lambda e: print("done", e),
                    )
                    while self.vc.is_playing():
                        await discord.utils.sleep_until(
                            discord.utils.utcnow() + timedelta(seconds=1)
                        )

                    self.IS_EXECUTING_COMMAND = False
                    await self.vc.disconnect()

        @self.client.command()
        async def chato(ctx, member: discord.Member):
            if member.voice is None:
                await ctx.send(f"{member.name} não está em uma call.")
                return

            await ctx.send(
                f"Vote no membro {member.name} para ser expulso da call. Reaja com 👍 para tirar ele da call ou com 👎 para não retirar ele da call"
            )

            votacao_msg = await ctx.send("Vote aqui!")
            await asyncio.gather(
                votacao_msg.add_reaction("👍"), votacao_msg.add_reaction("👎")
            )

            tempo_votacao = 6
            await asyncio.sleep(tempo_votacao)

            await ctx.send("Votação encerrada!")

            votacao_msg = await ctx.fetch_message(votacao_msg.id)

            reacoes = votacao_msg.reactions
            votos_positivos = 0
            votos_negativos = 0
            for reacao in reacoes:
                if reacao.emoji == "👍":
                    votos_positivos = reacao.count
                elif reacao.emoji == "👎":
                    votos_negativos = reacao.count

            if votos_positivos > votos_negativos:
                try:
                    await asyncio.gather(
                        member.move_to(None),
                        ctx.send(
                            f"{member.name} foi removido da call com {votos_positivos} votos a favor e {votos_negativos} votos contra."
                        ),
                    )
                except Exception as e:
                    await ctx.send(
                        f"Não foi possível remover {member.name} da call. Erro: {e}"
                    )
            else:
                await ctx.send(
                    f"{member.name} permanecerá na call. Votos a favor: {votos_positivos}, votos contra: {votos_negativos}"
                )

        @self.client.command()
        async def tocar(ctx):
            await tocarFunc(ctx, self)

        @self.client.command()
        async def silence(ctx,member: discord.Member = None):
            if member is None:
                await silenceFunc(ctx, self)
                return
            await silenceMemberFunc(ctx, self, member)

        @self.client.command(aliases=["yt"])
        async def youtube(ctx, link):
            await youtubeFunc(ctx, link, self)
            
        @self.client.command()
        async def showQueue(ctx):
            if len(self.QUEUE) == 0:
                embed = discord.Embed(
                    title="Fila de reprodução",
                    description="Nenhuma música na fila.",
                    color=discord.Color.red(),
                )
                return await ctx.send(embed=embed)
            await ctx.send(embed=showYtQueue(self.QUEUE))

        @self.client.command()
        async def gpt(ctx, message=" "):
            def check_author(m):
                return m.author == ctx.author

            if self.IS_EXECUTING_COMMAND:
                await ctx.send("Bot ocupado no momento.")
                return

            self.IS_EXECUTING_COMMAND = True
            chat = Gemini().startModel().start_chat(history=[])
            prompt = message
            await ctx.send(
                'Sua conversa com o vitola bot vai começar! Digite "fim" para encerrar a conversa.'
            )

            while prompt != "fim":
                response = chat.send_message(prompt)
                await ctx.send(response.text)

                prompt = await self.client.wait_for("message", check=check_author)
                prompt = prompt.content

            self.IS_EXECUTING_COMMAND = False
            await ctx.send("Conversa com o vitola bot encerrada!")

        @self.client.command()
        async def help(ctx):
            embed = discord.Embed(
                title="Lista de Comandos",
                description="Aqui estão todos os comandos disponíveis:",
                color=discord.Color.blue(),
            )
            embed.add_field(name="!chato <member>", value="Inicia uma votação para expulsar um membro da call.", inline=False)
            embed.add_field(name="!tocar", value="Toca uma música na call.", inline=False)
            embed.add_field(name="!silence [member]", value="Silencia um membro ou todos na call.", inline=False)
            embed.add_field(name="!youtube <link> or !yt <link>", value="Adiciona uma música do youtube na fila de reprodução.", inline=False)
            embed.add_field(name="!yt quit", value="Encerra a fila de reprodução.", inline=False)
            embed.add_field(name="!yt next", value="Pula para a próxima música da fila.", inline=False)
            embed.add_field(name="!showQueue", value="Mostra a fila de reprodução.", inline=False)
            embed.add_field(name="!gpt [message]", value="Inicia uma conversa com o bot GPT.", inline=False)
            await ctx.send(embed=embed)

        @self.client.event
        async def on_message(message):
            if message.author == self.client.user:
                return

            username = message.author
            user_message = message.content
            channel = message.channel

            if str(channel.id) == self.CODIGO_CHANNEL_TOKEN:
                code = f"```python\n{user_message}\n```"
                await message.delete()
                await self.send_message_to_chat(self.client, code, channel.id)

            if username == "chaul0205":
                await message.add_reaction("<:Chaul:1243037858907029534>")
            if username == "humberto_cunha":
                await message.add_reaction("🐺")
            if username == "brunodss":
                await message.reply("Você é PUTA RAPAZ!")

            await self.client.process_commands(message)

        try:
            self.client.run(self.TOKEN)
        except Exception as e:
            write_error_log(e)
            files = glob.glob('assets/tempAudios/*')
            for f in files:
                os.remove(f)
            exit(1)

    async def call_next_in_QUEUE(self):
        next_command = self.QUEUE.pop(0)
        command_type = next_command['type']
        if command_type == 'youtube':
            await youtubeFunc(next_command['ctx'], next_command['link'], self)
        elif command_type == 'silence':
            await silenceFunc(next_command['ctx'])
        elif command_type == 'tocar':
            await tocarFunc(next_command['ctx'])
        else:
            raise TypeError('Command type does not match.')

