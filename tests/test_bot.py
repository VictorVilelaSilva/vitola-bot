from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from discord.ext import commands

from src.cogs.community import CommunityCog
from src.config import Settings
from src.DiscordBot import DiscordBot
from src.utils import require_voice


async def test_startup_loads_cogs_and_preserves_command_names_without_login():
    async with DiscordBot(Settings()) as bot:
        await bot.setup_hook()
        assert isinstance(bot, commands.Bot)
        for name in (
            "tocar",
            "ripita",
            "autismo",
            "bahiano",
            "rj",
            "youtube",
            "yt",
            "video",
            "baixarvideo",
            "mp3",
            "showQueue",
            "silence",
            "chato",
            "gpt",
            "comandos",
            "fim",
        ):
            assert bot.get_command(name) is not None
        assert bot.get_command("silence").cog is bot.get_cog("Moderação")
        assert bot.get_command("gpt").clean_params["message"].kind.name == "KEYWORD_ONLY"
        assert all(
            isinstance(bot.get_command(name), commands.HybridCommand)
            for name in (
                "tocar",
                "ripita",
                "autismo",
                "bahiano",
                "rj",
                "youtube",
                "video",
                "mp3",
                "fila",
                "silence",
                "chato",
                "gpt",
                "fim",
                "comandos",
            )
        )
        assert {command.name for command in bot.tree.get_commands()} == {
            "tocar",
            "ripita",
            "autismo",
            "bahiano",
            "rj",
            "youtube",
            "video",
            "mp3",
            "fila",
            "silence",
            "chato",
            "gpt",
            "fim",
            "comandos",
        }
        music = bot.get_cog("Música")
        assert music.get_player(SimpleNamespace(id=1)) is not music.get_player(
            SimpleNamespace(id=2)
        )
        # Empty fake guilds must still support the player's shutdown contract.
        for player in music.players.values():
            player.guild.voice_client = None


def test_voice_command_validation_handles_no_voice_and_dms(context):
    context.author.voice = None
    with pytest.raises(commands.CheckFailure, match="canal de voz"):
        require_voice(context)
    context.guild = None
    with pytest.raises(commands.NoPrivateMessage):
        require_voice(context)


async def test_formatter_sends_before_deleting_original(context):
    bot = SimpleNamespace(settings=Settings(code_channel_id=context.channel.id))
    cog = CommunityCog(bot)
    order = []
    context.channel.send.side_effect = lambda *args, **kwargs: order.append("send")
    message = SimpleNamespace(
        author=context.author,
        guild=context.guild,
        channel=context.channel,
        content="print(1)",
        attachments=[],
        delete=AsyncMock(side_effect=lambda: order.append("delete")),
    )
    await cog.on_message(message)
    assert order == ["send", "delete"]


async def test_formatter_preserves_attachments_and_long_messages(context):
    cog = CommunityCog(SimpleNamespace(settings=Settings(code_channel_id=context.channel.id)))
    for text, attachments in [("x" * 2000, []), ("arquivo", [object()])]:
        message = SimpleNamespace(
            author=context.author,
            guild=context.guild,
            channel=context.channel,
            content=text,
            attachments=attachments,
            delete=AsyncMock(),
        )
        await cog.on_message(message)
        message.delete.assert_not_called()


def test_settings_validate_numbers_and_hide_secrets(monkeypatch):
    monkeypatch.setenv("DISCORD_TOKEN", "secret-discord")
    monkeypatch.setenv("GEMINI_API_KEY", "secret-google")
    monkeypatch.setenv("CODIGO_DISCORD_CHANNEL_ID_TOKEN", "123")
    settings = Settings.from_env()
    assert settings.code_channel_id == 123
    assert "secret" not in repr(settings)
    monkeypatch.setenv("AUDIO_QUEUE_SIZE", "0")
    with pytest.raises(ValueError, match="AUDIO_QUEUE_SIZE"):
        Settings.from_env()


async def test_sigterm_cancels_start_and_closes_bot(monkeypatch):
    import asyncio
    import signal

    import main
    from tests.conftest import wait_until

    handlers = {}
    closed = asyncio.Event()
    started = asyncio.Event()

    class FakeBot:
        def __init__(self, settings):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            closed.set()

        async def start(self, token):
            started.set()
            await asyncio.Event().wait()

    loop = asyncio.get_running_loop()
    monkeypatch.setattr(main, "DiscordBot", FakeBot)
    monkeypatch.setattr(
        loop, "add_signal_handler", lambda sig, callback: handlers.update({sig: callback})
    )
    monkeypatch.setattr(loop, "remove_signal_handler", lambda sig: handlers.pop(sig, None))
    task = asyncio.create_task(main.run_bot(Settings()))
    await started.wait()
    await wait_until(lambda: signal.SIGTERM in handlers)
    handlers[signal.SIGTERM]()
    await asyncio.wait_for(task, 1)
    assert closed.is_set()
    assert not handlers
