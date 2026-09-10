import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from src.cogs.chat import ChatCog
from src.config import Settings
from src.services.gemini import GeminiService
from tests.conftest import wait_until


def make_cog(context, **settings):
    bot = SimpleNamespace(settings=Settings(**settings), wait_for=AsyncMock())
    cog = ChatCog(bot)
    cog.service = SimpleNamespace(
        start_chat=Mock(return_value=object()),
        send=AsyncMock(return_value="Resposta"),
        close=AsyncMock(),
    )
    return cog


def test_message_filter_isolates_guild_channel_author_and_bots(context):
    key = ChatCog.session_key(context)
    message = SimpleNamespace(
        guild=context.guild, channel=context.channel, author=context.author, content="Olá"
    )
    assert ChatCog.accepts_message(message, key)
    for field, value in [
        ("guild", SimpleNamespace(id=2)),
        ("guild", None),
        ("channel", SimpleNamespace(id=99)),
        ("author", SimpleNamespace(id=500, bot=False)),
        ("author", SimpleNamespace(id=context.author.id, bot=True)),
        ("content", "!yt next"),
    ]:
        changed = SimpleNamespace(**vars(message))
        setattr(changed, field, value)
        assert not ChatCog.accepts_message(changed, key)


async def test_full_prompt_and_long_response_then_idle_cleanup(context):
    cog = make_cog(context)
    cog.service.send.return_value = "A" * 4100
    cog.bot.wait_for.side_effect = TimeoutError
    await cog.gpt.callback(cog, context, message="Explique toda esta frase")
    task = cog.sessions[cog.session_key(context)]
    await task
    cog.service.send.assert_awaited_once()
    assert cog.service.send.await_args.args[1] == "Explique toda esta frase"
    texts = [call.args[0] for call in context.send.await_args_list]
    assert "".join(text for text in texts if text.startswith("A")) == "A" * 4100
    assert all(len(text) <= 2000 for text in texts)
    assert "inatividade" in texts[-1]
    assert not cog.sessions


async def test_api_failure_releases_session_for_retry(context):
    cog = make_cog(context)
    cog.service.send.side_effect = RuntimeError("API unavailable")
    await cog.gpt.callback(cog, context, message="Olá")
    await cog.sessions[cog.session_key(context)]
    assert not cog.sessions
    cog.service.send.side_effect = None
    cog.bot.wait_for.side_effect = TimeoutError
    await cog.gpt.callback(cog, context, message="De novo")
    await cog.sessions[cog.session_key(context)]
    assert not cog.sessions
    assert cog.service.send.await_count == 2


async def test_cancel_during_request_releases_session(context):
    cog = make_cog(context)
    started = asyncio.Event()

    async def slow_send(*args):
        started.set()
        await asyncio.Event().wait()

    cog.service.send.side_effect = slow_send
    await cog.gpt.callback(cog, context, message="Olá")
    await started.wait()
    await cog.end_session.callback(cog, context)
    assert not cog.sessions
    assert context.send.await_args.args[0] == "Conversa encerrada."


async def test_cancel_before_session_task_starts(context):
    cog = make_cog(context)
    await cog.gpt.callback(cog, context, message="Olá")
    await cog.end_session.callback(cog, context)
    assert not cog.sessions
    cog.service.send.assert_not_awaited()


async def test_two_channels_have_independent_sessions(context):
    cog = make_cog(context)
    waiting = asyncio.Event()

    async def wait_for(*args, **kwargs):
        await waiting.wait()

    cog.bot.wait_for.side_effect = wait_for
    other = SimpleNamespace(**vars(context))
    other.channel = SimpleNamespace(id=21)
    await cog.gpt.callback(cog, context)
    await cog.gpt.callback(cog, other)
    try:
        await wait_until(lambda: cog.bot.wait_for.await_count == 2)
        assert len(cog.sessions) == 2
        await cog.end_session.callback(cog, context)
        assert list(cog.sessions) == [(context.guild.id, 21, context.author.id)]
    finally:
        await cog.cog_unload()


async def test_missing_api_key_does_not_create_session(context):
    cog = ChatCog(SimpleNamespace(settings=Settings()))
    from discord.ext import commands

    with pytest.raises(commands.CheckFailure, match="GEMINI_API_KEY"):
        await cog.gpt.callback(cog, context, message="Olá")
    assert not cog.sessions


async def test_gemini_service_uses_async_client_and_configured_model(monkeypatch):
    async_client = SimpleNamespace(
        chats=SimpleNamespace(create=Mock(return_value="chat")), aclose=AsyncMock()
    )
    client = SimpleNamespace(aio=async_client, close=Mock())
    factory = Mock(return_value=client)
    monkeypatch.setattr("src.services.gemini.genai.Client", factory)
    service = GeminiService(Settings(gemini_api_key="fake-key", gemini_model="configured-model"))
    assert service.start_chat() == "chat"
    assert async_client.chats.create.call_args.kwargs["model"] == "configured-model"
    chat = SimpleNamespace(send_message=AsyncMock(return_value=SimpleNamespace(text="Resposta")))
    assert await service.send(chat, "Olá") == "Resposta"
    chat.send_message.assert_awaited_once_with("Olá")
    await service.close()
    async_client.aclose.assert_awaited_once()
    client.close.assert_called_once()


async def test_request_timeout_is_bounded():
    service = GeminiService(Settings(chat_request_timeout=0.01))

    async def slow_send(*args):
        await asyncio.Event().wait()

    with pytest.raises(TimeoutError):
        await service.send(SimpleNamespace(send_message=slow_send), "Olá")
