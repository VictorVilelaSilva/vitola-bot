import asyncio
import logging
from contextlib import suppress

import discord
from discord import app_commands
from discord.ext import commands

from src.services.gemini import GeminiService
from src.utils import send_text

log = logging.getLogger(__name__)


class ChatCog(commands.Cog, name="Conversa"):
    def __init__(self, bot):
        self.bot = bot
        self.service = GeminiService(bot.settings)
        self.sessions: dict[tuple[int, int, int], asyncio.Task] = {}

    async def cog_check(self, ctx):
        if ctx.guild is None:
            raise commands.NoPrivateMessage()
        return True

    @staticmethod
    def session_key(ctx):
        return (ctx.guild.id, ctx.channel.id, ctx.author.id)

    @staticmethod
    def accepts_message(message, key):
        return (
            not message.author.bot
            and getattr(message.guild, "id", None) == key[0]
            and message.channel.id == key[1]
            and message.author.id == key[2]
            and not message.content.startswith("!")
        )

    @commands.hybrid_command(help="Conversa com a IA neste canal. Use fim ou !fim para encerrar.")
    @app_commands.describe(message="Mensagem inicial para a IA (opcional)")
    @commands.cooldown(1, 5, commands.BucketType.member)
    async def gpt(self, ctx, *, message: str = ""):
        await ctx.defer()
        key = self.session_key(ctx)
        if message.strip().lower() == "fim":
            await self._end_session(ctx)
            return
        if key in self.sessions:
            await ctx.send("Sua conversa já está aberta neste canal. Use !fim para encerrar.")
            return
        if len(self.sessions) >= self.bot.settings.chat_max_sessions:
            await ctx.send(
                "O limite de conversas simultâneas foi atingido. Tente novamente em instantes."
            )
            return
        try:
            chat = self.service.start_chat()
        except ValueError as error:
            raise commands.CheckFailure(str(error)) from error
        self.sessions[key] = asyncio.create_task(
            self._conversation(ctx, key, chat, message.strip()),
            name=f"chat-{key}",
        )

    async def _conversation(self, ctx, key, chat, prompt):
        try:
            await ctx.send('Conversa iniciada neste canal. Digite "fim" ou use !fim para encerrar.')
            for _ in range(self.bot.settings.chat_max_turns):
                if not prompt:
                    try:
                        message = await self.bot.wait_for(
                            "message",
                            check=lambda candidate: self.accepts_message(candidate, key),
                            timeout=self.bot.settings.chat_idle_timeout,
                        )
                    except TimeoutError:
                        await ctx.send("Conversa encerrada por inatividade.")
                        return
                    prompt = message.content.strip()
                if prompt.lower() == "fim":
                    await ctx.send("Conversa encerrada.")
                    return
                if not prompt:
                    continue
                if len(prompt) > 4000:
                    await ctx.send("Envie uma mensagem de até 4.000 caracteres.")
                else:
                    response = await self.service.send(chat, prompt)
                    await send_text(ctx, response)
                prompt = ""
            await ctx.send(
                "Conversa encerrada por atingir o limite de mensagens. Use !gpt para iniciar outra."
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Falha na conversa %s", key)
            try:
                await ctx.send(
                    "Não consegui consultar a IA. A conversa foi encerrada; tente !gpt novamente."
                )
            except discord.HTTPException:
                log.warning(
                    "Não foi possível avisar o canal sobre o encerramento da conversa %s", key
                )
        finally:
            if self.sessions.get(key) is asyncio.current_task():
                self.sessions.pop(key, None)

    @commands.hybrid_command(
        name="fim",
        help="Encerra sua conversa com a IA neste canal, inclusive durante uma consulta.",
    )
    async def end_session(self, ctx):
        await self._end_session(ctx)

    async def _end_session(self, ctx):
        task = self.sessions.get(self.session_key(ctx))
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            # A task cancelled before its first step never executes its finally block.
            self.sessions.pop(self.session_key(ctx), None)
        await ctx.send(
            "Conversa encerrada." if task else "Você não tem uma conversa aberta neste canal."
        )

    @commands.hybrid_command(help="Mostra os comandos disponíveis.")
    async def comandos(self, ctx):
        embed = discord.Embed(
            title="🤖 Central de comandos do Vitola",
            description=(
                "Digite `/` para escolher um comando na lista. "
                "Os comandos antigos com `!` continuam funcionando."
            ),
            color=discord.Color.red(),
        )
        embed.add_field(
            name="🎵 Música",
            value=(
                "`/youtube link:<url>` • `!yt <url>` — adiciona à fila\n"
                "`/youtube link:next` • `!yt next` — pula o áudio atual\n"
                "`/youtube link:quit` • `!yt quit` — limpa a fila\n"
                "`/fila` • `!fila` — mostra a fila de reprodução"
            ),
            inline=False,
        )
        embed.add_field(
            name="🎬 Download",
            value=(
                "`/video link:<url>` • `!video <url>` — baixa e envia o vídeo\n"
                "`/mp3 link:<url>` • `!mp3 <url>` — extrai e envia o áudio\n"
                "Alias antigo: `!baixarvideo <url>` • limite padrão de 10 MiB"
            ),
            inline=False,
        )
        embed.add_field(
            name="🔊 Áudios rápidos",
            value="`/tocar` • `/ripita` • `/autismo` • `/bahiano` • `/rj`",
            inline=False,
        )
        embed.add_field(
            name="🛡️ Moderação",
            value=(
                "`/silence [member]` • `!silence [@membro]` — silencia um ou todos\n"
                "`/chato member` • `!chato @membro` — abre votação para remover"
            ),
            inline=False,
        )
        embed.add_field(
            name="🧠 Inteligência artificial",
            value=(
                "`/gpt [message]` • `!gpt [mensagem]` — inicia uma conversa\n"
                "`/fim` • `!fim` — encerra sua conversa atual"
            ),
            inline=False,
        )
        embed.set_footer(text="Use /comandos ou !help <comando> para ver mais detalhes.")
        await ctx.send(embed=embed)

    async def cog_unload(self):
        tasks = list(self.sessions.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self.sessions.clear()
        await self.service.close()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        keys = [key for key in self.sessions if key[0] == guild.id]
        tasks = [self.sessions.pop(key) for key in keys]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def setup(bot):
    await bot.add_cog(ChatCog(bot))
