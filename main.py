import asyncio
import logging
import signal

from dotenv import load_dotenv

from src.config import Settings
from src.DiscordBot import DiscordBot


async def run_bot(settings: Settings):
    async with DiscordBot(settings) as bot:
        task = asyncio.create_task(bot.start(settings.discord_token))
        loop = asyncio.get_running_loop()
        terminated = False

        def terminate():
            nonlocal terminated
            terminated = True
            task.cancel()

        handler_installed = False
        try:
            try:
                loop.add_signal_handler(signal.SIGTERM, terminate)
                handler_installed = True
            except NotImplementedError:
                # Windows still receives graceful Ctrl+C handling from asyncio.run.
                pass
            await task
        except asyncio.CancelledError:
            if not terminated:
                raise
        finally:
            if handler_installed:
                loop.remove_signal_handler(signal.SIGTERM)
            # The bot context unloads Cogs before closing its HTTP session.


def main():
    load_dotenv()
    settings = Settings.from_env()
    if not settings.discord_token:
        raise SystemExit("Configure DISCORD_TOKEN no arquivo .env.")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(run_bot(settings))


if __name__ == "__main__":
    main()
