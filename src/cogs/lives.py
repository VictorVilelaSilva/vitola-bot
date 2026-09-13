import asyncio
import logging
import time

import discord
from aiohttp import web
from discord.ext import commands

from src.services.livekit_webhook import WebhookError, screen_share_started, verify_webhook

log = logging.getLogger(__name__)

WEBHOOK_PATH = "/livekit/webhook"
MAX_BODY_BYTES = 64 * 1024


class LivesCog(commands.Cog, name="Lives"):
    def __init__(self, bot):
        self.bot = bot
        self._runner: web.AppRunner | None = None
        self._last_notice: dict[str, float] = {}
        self._tasks: set[asyncio.Task] = set()

    @property
    def enabled(self) -> bool:
        settings = self.bot.settings
        return bool(settings.live_channel_id and settings.livekit_webhook_secret)

    def build_app(self) -> web.Application:
        app = web.Application(client_max_size=MAX_BODY_BYTES)
        app.router.add_post(WEBHOOK_PATH, self.handle_webhook)
        return app

    async def cog_load(self):
        if not self.enabled:
            log.info(
                "Avisos de live desativados: configure LIVE_CHANNEL_ID e LIVEKIT_WEBHOOK_SECRET."
            )
            return
        settings = self.bot.settings
        runner = web.AppRunner(self.build_app(), access_log=None)
        await runner.setup()
        try:
            await web.TCPSite(
                runner, settings.live_webhook_host, settings.live_webhook_port
            ).start()
        except OSError:
            await runner.cleanup()
            raise
        self._runner = runner
        log.info(
            "Webhook de lives ouvindo em %s:%s%s",
            settings.live_webhook_host,
            settings.live_webhook_port,
            WEBHOOK_PATH,
        )

    async def cog_unload(self):
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None

    async def handle_webhook(self, request: web.Request) -> web.Response:
        settings = self.bot.settings
        body = await request.read()
        try:
            event = verify_webhook(
                body,
                request.headers.get("Authorization"),
                api_key=settings.livekit_webhook_key,
                api_secret=settings.livekit_webhook_secret,
            )
        except WebhookError as error:
            log.warning("Webhook do LiveKit recusado: %s", error)
            return web.Response(status=401)

        live = screen_share_started(event)
        if live is not None and self._should_notify(live.user_id):
            # Responde antes de falar com o Discord: se o envio demorar, o LiveKit
            # não fica esperando nem reenvia o mesmo evento.
            task = asyncio.create_task(self.announce(live.name))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
        return web.Response(status=200)

    def _should_notify(self, user_id: str) -> bool:
        # Uma queda de conexão republica a track; sem o intervalo, cada
        # reconexão viraria um aviso novo no canal.
        now = time.monotonic()
        last = self._last_notice.get(user_id)
        if last is not None and now - last < self.bot.settings.live_cooldown:
            return False
        self._last_notice[user_id] = now
        return True

    async def announce(self, name: str):
        settings = self.bot.settings
        content = (
            f"🔴 **{discord.utils.escape_markdown(name)}** começou uma live! "
            f"Assista em {settings.live_url}"
        )
        try:
            channel = self.bot.get_channel(settings.live_channel_id)
            if channel is None:
                channel = await self.bot.fetch_channel(settings.live_channel_id)
            await channel.send(content, allowed_mentions=discord.AllowedMentions.none())
        except discord.HTTPException:
            log.warning("Não foi possível avisar a live no canal %s", settings.live_channel_id)


async def setup(bot):
    await bot.add_cog(LivesCog(bot))
