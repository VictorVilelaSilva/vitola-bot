import asyncio
import base64
import hashlib
import hmac
import json
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import discord
import pytest
from aiohttp.test_utils import TestClient, TestServer

from src.cogs.lives import WEBHOOK_PATH, LivesCog
from src.config import Settings
from src.services.livekit_webhook import (
    LiveStart,
    WebhookError,
    screen_share_started,
    verify_webhook,
)

AVATAR = "https://cdn.discordapp.com/avatars/123456/abc.png"
DEFAULT_AVATAR = "https://cdn.discordapp.com/embed/avatars/0.png"
KEY = "webhook"
SECRET = "segredo-de-teste-com-mais-de-32-caracteres"


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def sign(body: bytes, *, key=KEY, secret=SECRET, alg="HS256", **overrides) -> str:
    now = int(time.time())
    claims = {
        "iss": key,
        "nbf": now,
        "exp": now + 300,
        "sha256": base64.b64encode(hashlib.sha256(body).digest()).decode(),
    }
    claims.update(overrides)
    header = b64url(json.dumps({"alg": alg, "typ": "JWT"}).encode())
    payload = b64url(json.dumps(claims).encode())
    signature = hmac.new(secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256)
    return f"{header}.{payload}.{b64url(signature.digest())}"


def screen_share(
    identity="123456#ab12cd34", name=None, source="SCREEN_SHARE", avatar=None
) -> bytes:
    # Formato real: no track_published o LiveKit só envia sid e identity do participante.
    participant = {"sid": "PA_1", "identity": identity}
    if name is not None:
        participant["name"] = name
    if avatar is not None:
        participant["metadata"] = json.dumps({"avatarUrl": avatar})
    return json.dumps(
        {
            "event": "track_published",
            "room": {"name": "geral"},
            "participant": participant,
            "track": {"sid": "TR_1", "type": "VIDEO", "source": source},
        }
    ).encode()


def verify(body, authorization):
    return verify_webhook(body, authorization, api_key=KEY, api_secret=SECRET)


def test_accepts_signed_event_with_or_without_bearer():
    body = screen_share()
    token = sign(body)
    assert verify(body, token)["event"] == "track_published"
    assert verify(body, f"Bearer {token}")["event"] == "track_published"


@pytest.mark.parametrize(
    "authorization",
    [
        None,
        "",
        "não-é-jwt",
        sign(screen_share(), secret="outro-segredo-com-mais-de-32-caracteres"),
        sign(screen_share(), key="devkey"),
        sign(screen_share(), alg="none"),
        sign(screen_share(), exp=int(time.time()) - 60),
        sign(screen_share(), nbf=int(time.time()) + 60),
        sign(b"outro corpo"),
    ],
)
def test_rejects_unsigned_forged_expired_or_tampered_requests(authorization):
    with pytest.raises(WebhookError):
        verify(screen_share(), authorization)


def test_recognizes_only_screen_share_publications():
    assert screen_share_started(json.loads(screen_share())) == ("123456", "Alguém", None)
    live = screen_share_started(json.loads(screen_share(name="Fulano", avatar=AVATAR)))
    assert live == ("123456", "Fulano", AVATAR)
    elsewhere = screen_share(avatar="https://exemplo.com/a.png")
    assert screen_share_started(json.loads(elsewhere)).avatar_url is None
    broken = json.loads(screen_share())
    broken["participant"]["metadata"] = "{não é json"
    assert screen_share_started(broken).avatar_url is None
    assert screen_share_started(json.loads(screen_share(source="CAMERA"))) is None
    assert screen_share_started(json.loads(screen_share(source="SCREEN_SHARE_AUDIO"))) is None
    left = json.loads(screen_share())
    left["event"] = "track_unpublished"
    assert screen_share_started(left) is None
    assert screen_share_started({"event": "track_published"}) is None
    assert screen_share_started(json.loads(screen_share(name="  "))).name == "Alguém"


def make_user(name, avatar=AVATAR):
    return SimpleNamespace(display_name=name, display_avatar=SimpleNamespace(url=avatar))


def lookup(found):
    async def fetch(user_id):
        if user_id in found:
            return found[user_id]
        raise discord.NotFound(Mock(status=404, reason="Not Found"), "Unknown User")

    return AsyncMock(side_effect=fetch)


def make_cog(members=None, users=None, **settings):
    guild = SimpleNamespace(get_member=lambda _: None, fetch_member=lookup(members or {}))
    channel = SimpleNamespace(guild=guild, send=AsyncMock())
    bot = SimpleNamespace(
        settings=Settings(
            live_channel_id=576190309688672257,
            livekit_webhook_secret=SECRET,
            **settings,
        ),
        get_channel=lambda _: channel,
        fetch_channel=AsyncMock(),
        fetch_user=lookup(users or {}),
    )
    return LivesCog(bot), channel


async def post(client, body, authorization):
    response = await client.post(WEBHOOK_PATH, data=body, headers={"Authorization": authorization})
    return response.status


async def test_webhook_announces_live_with_discord_profile_once_per_cooldown():
    cog, channel = make_cog(
        members={123456: make_user("@everyone *vitola*")},
        users={999: make_user("Beltrano", avatar=DEFAULT_AVATAR)},
    )
    async with TestClient(TestServer(cog.build_app())) as client:
        body = screen_share()
        assert await post(client, body, sign(body)) == 200
        # Mesma pessoa em outra aba, logo após uma reconexão.
        again = screen_share(identity="123456#ffffffff")
        assert await post(client, again, sign(again)) == 200
        # Quem não está mais no servidor ainda é encontrado como usuário.
        other = screen_share(identity="999#00000000")
        assert await post(client, other, sign(other)) == 200
        await asyncio.gather(*cog._tasks)

    assert channel.send.await_count == 2
    first, second = (call.kwargs for call in channel.send.await_args_list)
    assert first["embed"].title == "🔴 @everyone \\*vitola\\* está ao vivo!"
    assert first["embed"].thumbnail.url == AVATAR
    [button] = first["view"].children
    assert button.style is discord.ButtonStyle.link
    assert button.url == "https://fckjj.vitolas.com.br"
    assert button.label == "Assistir live"
    allowed = first["allowed_mentions"]
    assert not allowed.everyone and not allowed.users and not allowed.roles
    assert second["embed"].title == "🔴 Beltrano está ao vivo!"
    assert second["embed"].thumbnail.url == DEFAULT_AVATAR


async def test_announcement_falls_back_to_webhook_data_when_discord_lookup_fails():
    cog, channel = make_cog()
    await cog.announce(LiveStart("123456", "Fulano", AVATAR))
    await cog.announce(LiveStart("não-numérico", "Alguém", None))

    cog.bot.fetch_user.assert_awaited_once_with(123456)
    first, second = (call.kwargs for call in channel.send.await_args_list)
    assert first["embed"].title == "🔴 Fulano está ao vivo!"
    assert first["embed"].thumbnail.url == AVATAR
    assert second["embed"].title == "🔴 Alguém está ao vivo!"
    assert second["embed"].thumbnail.url is None


async def test_webhook_rejects_bad_signature_and_ignores_cameras():
    cog, channel = make_cog()
    async with TestClient(TestServer(cog.build_app())) as client:
        body = screen_share()
        forged = sign(body, secret="outro-segredo-com-mais-de-32-caracteres")
        assert await post(client, body, forged) == 401
        camera = screen_share(source="CAMERA")
        assert await post(client, camera, sign(camera)) == 200
        await asyncio.gather(*cog._tasks)
    channel.send.assert_not_awaited()


async def test_cog_stays_offline_without_configuration_and_serves_when_configured():
    disabled = LivesCog(SimpleNamespace(settings=Settings()))
    await disabled.cog_load()
    assert disabled._runner is None

    cog, _ = make_cog(live_webhook_host="127.0.0.1", live_webhook_port=48026)
    await cog.cog_load()
    try:
        assert cog._runner is not None and cog._runner.addresses
    finally:
        await cog.cog_unload()
    assert cog._runner is None
