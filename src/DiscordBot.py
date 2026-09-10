import logging

import discord
from discord.ext import commands

from src.config import Settings

log = logging.getLogger(__name__)


class DiscordBot(commands.Bot):
    def __init__(self, settings: Settings):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(
            command_prefix="!",
            intents=intents,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        self.settings = settings

    async def setup_hook(self):
        for extension in ("music", "moderation", "chat", "community"):
            await self.load_extension(f"src.cogs.{extension}")

    async def on_ready(self):
        log.info("Vitola bot online: %s", self.user)

    async def on_command_error(self, ctx, error):
        if ctx.command and ctx.command.has_error_handler():
            return
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.CommandOnCooldown):
            message = f"Aguarde {error.retry_after:.0f}s para usar esse comando novamente."
        elif isinstance(error, commands.BotMissingPermissions):
            message = "Estou sem as permissões necessárias: " + ", ".join(error.missing_permissions)
        elif isinstance(error, commands.MissingPermissions):
            message = "Você não tem as permissões necessárias para esse comando."
        elif isinstance(error, commands.NoPrivateMessage):
            message = "Use esse comando dentro de um servidor."
        elif isinstance(error, commands.MaxConcurrencyReached):
            message = "Já existe uma operação desse tipo em andamento."
        elif isinstance(error, commands.UserInputError):
            message = f"Argumentos inválidos. Consulte !help {ctx.command}."
        elif isinstance(error, commands.CheckFailure):
            message = str(error)
        else:
            original = getattr(error, "original", error)
            log.error(
                "Comando %s falhou no servidor %s",
                ctx.command,
                getattr(ctx.guild, "id", None),
                exc_info=(type(original), original, original.__traceback__),
            )
            message = "Não consegui concluir o comando. Tente novamente em instantes."
        try:
            await ctx.send(message)
        except discord.HTTPException:
            log.warning("Não foi possível enviar o erro do comando ao canal %s", ctx.channel.id)
