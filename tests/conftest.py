import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import discord
import pytest


class FakeVoice:
    def __init__(self, channel, *, auto_finish=True):
        self.channel = channel
        self.connected = True
        self.auto_finish = auto_finish
        self.after = None
        self.played = []
        self.started = asyncio.Event()

    def is_connected(self):
        return self.connected

    def play(self, source, *, after):
        self.played.append(source.path)
        self.after = after
        self.started.set()
        if self.auto_finish:
            after(None)

    def stop(self):
        if self.after:
            callback, self.after = self.after, None
            callback(None)

    async def disconnect(self, *, force=False):
        self.stop()
        self.connected = False
        self.channel.guild.voice_client = None

    async def move_to(self, channel):
        self.channel = channel


class FakeSource:
    def __init__(self, path, **kwargs):
        self.path = path
        self.cleaned = False

    def cleanup(self):
        self.cleaned = True


def make_member(guild, channel, user_id, *, muted=False, role=1, bot=False):
    member = SimpleNamespace(
        id=user_id,
        guild=guild,
        voice=SimpleNamespace(channel=channel, mute=muted),
        top_role=role,
        bot=bot,
        display_name=f"member-{user_id}",
        name=f"member-{user_id}",
        guild_permissions=discord.Permissions.all(),
    )

    async def edit(**kwargs):
        member.voice.mute = kwargs["mute"]

    member.edit = AsyncMock(side_effect=edit)
    member.move_to = AsyncMock()
    return member


@pytest.fixture
def context():
    guild = SimpleNamespace(id=1, owner_id=999, voice_client=None)
    channel = Mock(spec=discord.VoiceChannel)
    channel.id = 10
    channel.guild = guild
    channel.permissions_for.return_value = discord.Permissions.all()
    guild.me = make_member(guild, channel, 900, role=20, bot=True)
    author = make_member(guild, channel, 100, role=10)
    target = make_member(guild, channel, 101)
    channel.members = [author, target, guild.me]
    destination = SimpleNamespace(
        id=20, send=AsyncMock(), permissions_for=lambda _: discord.Permissions.all()
    )
    ctx = SimpleNamespace(
        guild=guild,
        author=author,
        me=guild.me,
        channel=destination,
        send=AsyncMock(),
        send_help=AsyncMock(),
        permissions=discord.Permissions.all(),
        bot_permissions=discord.Permissions.all(),
    )
    ctx.voice_channel = channel
    ctx.target = target
    return ctx


async def wait_until(predicate):
    async with asyncio.timeout(2):
        while not predicate():
            await asyncio.sleep(0)
