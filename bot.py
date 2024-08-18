from ast import alias
import discord
import helper
import asyncio
import os
from Gemini import Gemini
from datetime import timedelta
from discord.ext import commands


class DiscordBot:
    def __init__(self):
        self.QUEUE: list = []
        self.vc: discord.VoiceChannel = None
        self.IS_EXECUTING_COMMAND: bool = False
        self.CHANNEL_TOKEN = os.getenv("CHANNEL_TOKEN")
        self.TOKEN = os.getenv("DISCORD_TOKEN")
        self.CODIGO_CHANNEL_TOKEN = os.getenv("CODIGO_DISCORD_CHANNEL_ID_TOKEN")
        self.QUEUE_MESSAGE = (
            "Adicionado à fila. Será reproduzido quando o comando atual finalizar."
        )

    async def send_message_to_chat(client, message, channel_id):
        channel = client.get_channel(channel_id)
        await channel.send(message)

    def run_discord_bot(self):
        if self.TOKEN is None:
            print("Insira o DISCORD_TOKEN no arquivo .env")
            exit(1)
        intents = discord.Intents.default()
        intents.message_content = True
        client = commands.Bot(command_prefix="!", intents=intents)

        @client.event
        async def on_ready():
            print(f"Estrou on the line {client.user}")

        @client.event
        async def on_voice_state_update(member, before, after):
            if len(self.QUEUE):
                return

            if before.channel is None and after.channel is not None:
                if member.name == "humberto_cunha":
                    self.IS_EXECUTING_COMMAND = True
                    channel = after.channel
                    if self.vc is None or not self.vc.is_connected():
                        self.vc = await channel.connect()

                    file_path = "audios/lobinho.mp3"
                    if not os.path.isfile(file_path):
                        await self.send_message_to_chat(
                            client, "Arquivo não encontrado!", self.CODIGO_CHANNEL_TOKEN
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

        @client.command()
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

        @client.command()
        async def tocar(ctx):
            if self.IS_EXECUTING_COMMAND:
                self.QUEUE.append({"type": "tocar", "ctx": ctx})
                await ctx.send(
                    "Adicionado à fila. Será reproduzido quando o comando atual finalizar."
                )
                return

            self.IS_EXECUTING_COMMAND = True
            channel = ctx.author.voice.channel
            if channel is not None:
                if self.vc is None or not self.vc.is_connected():
                    self.vc = await channel.connect()

                file_path = "audios/lobinho.mp3"
                if not os.path.isfile(file_path):
                    await ctx.send("Arquivo não encontrado!")
                    await self.vc.disconnect()
                    return

                self.vc.play(
                    discord.FFmpegPCMAudio(file_path), after=lambda e: print("done", e)
                )

                while self.vc.is_playing():
                    await discord.utils.sleep_until(
                        discord.utils.utcnow() + timedelta(seconds=1)
                    )

                self.IS_EXECUTING_COMMAND = False
                if len(self.QUEUE):
                    await self.call_next_in_QUEUE()
                else:
                    await self.vc.disconnect()
            else:
                await ctx.send(
                    "Você precisa estar em um canal de voz para usar esse comando."
                )

        @client.command()
        async def silence(ctx):
            if self.IS_EXECUTING_COMMAND:
                self.QUEUE.append({"type": "silence", "ctx": ctx})
                await ctx.send(
                    "Adicionado à fila. Será reproduzido quando o comando atual finalizar."
                )
                return

            self.IS_EXECUTING_COMMAND = True
            channel = ctx.author.voice.channel
            if channel is not None:
                if self.vc is None or not self.vc.is_connected():
                    self.vc = await channel.connect()

                file_path = "audios/silencer.mp3"
                if not os.path.isfile(file_path):
                    await ctx.send("Arquivo não encontrado!")
                    await self.vc.disconnect()
                    return

                self.vc.play(
                    discord.FFmpegPCMAudio(file_path), after=lambda e: print("done", e)
                )

                for member in channel.members:
                    if member != client.user:
                        await member.edit(mute=True)

                while self.vc.is_playing():
                    await discord.utils.sleep_until(
                        discord.utils.utcnow() + timedelta(seconds=1)
                    )

                for member in channel.members:
                    await member.edit(mute=False)

                self.IS_EXECUTING_COMMAND = False
                if len(self.QUEUE):
                    await self.call_next_in_QUEUE()
                else:
                    await self.vc.disconnect()

        @client.command(aliases=["yt"])
        async def youtube(ctx, link):
            if self.IS_EXECUTING_COMMAND:
                self.QUEUE.append({"type": "youtube", "link": link, "ctx": ctx})
                await ctx.send(
                    "Adicionado à fila. Será reproduzido quando o comando atual finalizar."
                )
                return

            self.IS_EXECUTING_COMMAND = True
            channel = ctx.author.voice.channel
            if channel is not None:
                file_path = helper.download_video(link)
                if not os.path.isfile(file_path):
                    await ctx.send("Download mal sucedido.")
                    return

                if self.vc is None or not self.vc.is_connected():
                    self.vc = await channel.connect()

                self.vc.play(
                    discord.FFmpegPCMAudio(file_path), after=lambda e: print("done", e)
                )
                while self.vc.is_playing():
                    await discord.utils.sleep_until(
                        discord.utils.utcnow() + timedelta(seconds=1)
                    )

                os.remove(file_path)

                self.IS_EXECUTING_COMMAND = False
                if len(self.QUEUE):
                    await self.call_next_in_QUEUE()
                else:
                    await self.vc.disconnect()
            else:
                await ctx.send(
                    "Você precisa estar em um canal de voz para usar esse comando."
                )

        @client.command()
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

                prompt = await client.wait_for("message", check=check_author)
                prompt = prompt.content

            self.IS_EXECUTING_COMMAND = False
            await ctx.send("Conversa com o vitola bot encerrada!")

        @client.event
        async def on_message(message):
            if message.author == client.user:
                return

            username = message.author
            user_message = message.content
            channel = message.channel

            if str(channel.id) == self.CODIGO_CHANNEL_TOKEN:
                code = f"```python\n{user_message}\n```"
                await message.delete()
                await self.send_message_to_chat(client, code, channel.id)

            if username == "chaul0205":
                await message.add_reaction("<:Chaul:1243037858907029534>")
            if username == "humberto_cunha":
                await message.add_reaction("🐺")
            if username == "brunodss":
                await message.reply("Você é PUTA RAPAZ!")

            await client.process_commands(message)

        async def call_next_in_QUEUE(self):
            if len(self.QUEUE) > 0:
                next_command = self.QUEUE.pop(0)
                command_type = next_command.get("type")
                if command_type == "yt":
                    await self.youtube(next_command["ctx"], next_command["link"])
                elif command_type == "silence":
                    await self.silence(next_command["ctx"])
                elif command_type == "tocar":
                    await self.tocar(next_command["ctx"])
                else:
                    raise TypeError("Command type does not match.")

        client.run(self.TOKEN)
