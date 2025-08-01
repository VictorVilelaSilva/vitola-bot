from discord.ext import commands
import discord
import glob
import os

from src.commands.silence import silenceFunc, silenceMemberFunc
from src.commands.helpers.pathUtils import get_audio_path
from src.commands.helpers.helper import write_error_log
from src.commands.showQueue import showQueueFunc
from src.commands.youtube import youtubeFunc
from src.commands.tocar import tocarFunc
from src.commands.onVoiceUpdate import handle_on_voice_update


class DiscordBot:
    def __init__(self):
        self.QUEUE: list = []
        self.vc: discord.VoiceChannel = None
        self.IS_EXECUTING_COMMAND: bool = False
        self.CHANNEL_TOKEN = os.getenv("CHANNEL_TOKEN")
        self.TOKEN = os.getenv("DISCORD_TOKEN")
        self.CODIGO_CHANNEL_TOKEN = os.getenv("CODIGO_DISCORD_CHANNEL_ID_TOKEN")
        self.QUEUE_MESSAGE = (
            "Adicionado à fila. Será reproduzido quando a musica atual finalizar."
        )
        self.client = None

    async def send_message_to_chat(self, client, message, channel_id):
        channel = client.get_channel(channel_id)
        await channel.send(message)

    def init_bot(self):
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
                if await handle_on_voice_update(self, member, after):
                    return

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

        return self.client

    def run_discord_bot(self):
        bot = self.init_bot()
        try:
            bot.run(self.TOKEN)
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

