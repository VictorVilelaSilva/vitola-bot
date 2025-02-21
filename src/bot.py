from discord.ext import commands
from datetime import timedelta
import discord
import glob
import os

from src.commands.chato import chatoFunc
from src.commands.comandos import comandosFunc
from src.commands.gpt import gptFunc
from src.commands.helpers.helper import write_error_log
from src.commands.helpers.pathUtils import get_audio_path
from src.commands.showQueue import showQueueFunc
from src.commands.silence import silenceFunc, silenceMemberFunc
from src.commands.tocar import tocarFunc
from src.commands.youtube import youtubeFunc


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
            print(f"Vitola bot esta online {self.client.user}")

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

                    file_path = get_audio_path("lobinho.mp3")
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
            await chatoFunc(ctx, self, member)

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
            await showQueueFunc(ctx, self)

        @self.client.command()
        async def gpt(ctx, message=" "):
            await gptFunc(ctx, self, message)

        @self.client.command()
        async def comandos(ctx):
            await comandosFunc(ctx)

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

