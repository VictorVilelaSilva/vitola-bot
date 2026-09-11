import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest
from discord.ext import commands

from src.cogs.moderation import ModerationCog, VoteView, validate_target
from tests.conftest import make_member


async def test_existing_mute_is_preserved_after_failure(context):
    cog = ModerationCog(SimpleNamespace())
    existing = make_member(context.guild, context.voice_channel, 102, muted=True)
    with pytest.raises(RuntimeError):
        async with cog.temporary_mute(context, [existing, context.target], context.voice_channel):
            assert context.target.voice.mute is True
            raise RuntimeError("playback failed")
    assert existing.voice.mute is True
    existing.edit.assert_not_called()
    assert context.target.voice.mute is False
    assert [call.kwargs["mute"] for call in context.target.edit.await_args_list] == [True, False]


async def test_partial_mute_failure_restores_every_attempted_member(context):
    cog = ModerationCog(SimpleNamespace())
    other = make_member(context.guild, context.voice_channel, 102)

    async def fail_mute(**kwargs):
        if kwargs["mute"]:
            raise RuntimeError("permission changed")
        other.voice.mute = False

    other.edit.side_effect = fail_mute
    with pytest.raises(RuntimeError):
        async with cog.temporary_mute(context, [context.target, other], context.voice_channel):
            pytest.fail("Must not start playback after a failed mute.")
    assert context.target.voice.mute is False
    assert other.edit.await_args.kwargs["mute"] is False


async def test_cancellation_restores_mute(context):
    cog = ModerationCog(SimpleNamespace())
    started = asyncio.Event()

    async def operation():
        async with cog.temporary_mute(context, [context.target], context.voice_channel):
            started.set()
            await asyncio.Event().wait()

    task = asyncio.create_task(operation())
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert context.target.voice.mute is False


async def test_permissions_rechecked_when_queued_mute_starts(context):
    cog = ModerationCog(SimpleNamespace())
    context.voice_channel.permissions_for.return_value = discord.Permissions.none()
    with pytest.raises(commands.BotMissingPermissions):
        async with cog.temporary_mute(context, [context.target], context.voice_channel):
            pytest.fail("Missing permissions must prevent playback.")
    context.target.edit.assert_not_called()


async def test_commands_ignore_unrelated_text_channel_permissions(context):
    context.permissions = discord.Permissions.none()
    for command in (ModerationCog.silence, ModerationCog.chato):
        for check in command.checks:
            await discord.utils.maybe_coroutine(check, context)


@pytest.mark.parametrize(
    ("command", "permission"),
    [
        (ModerationCog.silence, "mute_members"),
        (ModerationCog.chato, "move_members"),
    ],
)
async def test_commands_reject_callers_without_voice_moderation_permission(
    context, command, permission
):
    author_permissions = discord.Permissions.all()
    author_permissions.update(**{permission: False})
    context.voice_channel.permissions_for.side_effect = lambda member: (
        discord.Permissions.all() if member is context.me else author_permissions
    )
    with pytest.raises(commands.MissingPermissions) as error:
        for check in command.checks:
            await discord.utils.maybe_coroutine(check, context)
    assert error.value.missing_permissions == [permission]


def test_target_accepts_owner_administrator_and_higher_roles(context):
    context.target.id = context.guild.owner_id
    context.target.top_role = context.guild.me.top_role + 1
    validate_target(context, context.target, context.voice_channel)


def test_target_must_be_human_and_in_same_channel(context):
    context.target.voice.channel = None
    with pytest.raises(commands.CheckFailure, match="mesmo canal"):
        validate_target(context, context.target, context.voice_channel)
    context.target.voice.channel = context.voice_channel
    context.target.bot = True
    with pytest.raises(commands.CheckFailure, match="bots"):
        validate_target(context, context.target, context.voice_channel)


async def test_silence_without_target_includes_owner_and_administrators(context):
    context.guild.owner_id = context.author.id
    context.author.top_role = context.guild.me.top_role + 2
    context.target.top_role = context.guild.me.top_role + 1
    music = SimpleNamespace(enqueue_local=AsyncMock())
    cog = ModerationCog(SimpleNamespace(get_cog=lambda name: music))

    await cog.silence.callback(cog, context)

    effect = music.enqueue_local.await_args.kwargs["effect"]
    async with effect():
        assert context.author.voice.mute is True
        assert context.target.voice.mute is True
        assert context.guild.me.voice.mute is False
    assert context.author.voice.mute is False
    assert context.target.voice.mute is False


async def test_vote_excludes_outsiders_and_bots_and_requires_quorum(context):
    voters = [
        make_member(context.guild, context.voice_channel, user_id) for user_id in (201, 202, 203)
    ]
    context.voice_channel.members.extend(voters)
    view = VoteView(context.voice_channel, {member.id for member in voters})
    assert not view.can_vote(context.target)
    assert not view.can_vote(context.guild.me)
    view.votes[201] = True
    assert view.result() == (1, 0, 2)
    # One member changing their vote still occupies one entry.
    view.votes[201] = False
    assert view.result() == (0, 1, 2)
    view.votes[201] = True
    view.votes[202] = True
    assert view.result() == (2, 0, 2)
    voters[1].voice.channel = None
    assert view.result() == (1, 0, 2)
    view.stop()


async def test_restore_failure_does_not_prevent_restoring_other_members(context):
    cog = ModerationCog(SimpleNamespace())
    other = make_member(context.guild, context.voice_channel, 102)

    async def fail_restore(**kwargs):
        if not kwargs["mute"]:
            raise RuntimeError("member disconnected")
        other.voice.mute = True

    other.edit.side_effect = fail_restore
    async with cog.temporary_mute(context, [other, context.target], context.voice_channel):
        pass
    assert context.target.voice.mute is False
    assert str(other.id) in context.send.await_args.args[0]


async def test_failed_removal_never_announces_success(context, monkeypatch):
    from unittest.mock import AsyncMock

    for user_id in (201, 202):
        context.voice_channel.members.append(
            make_member(context.guild, context.voice_channel, user_id)
        )

    class ImmediateVote(VoteView):
        async def wait(self):
            self.votes = {user_id: True for user_id in self.eligible_ids}

    monkeypatch.setattr("src.cogs.moderation.VoteView", ImmediateVote)
    context.send.return_value = SimpleNamespace(id=1000, edit=AsyncMock())
    context.target.move_to.side_effect = RuntimeError("Discord rejected removal")
    cog = ModerationCog(SimpleNamespace())
    with pytest.raises(RuntimeError):
        await cog.chato.callback(cog, context, context.target)
    assert not any("foi removido" in call.args[0] for call in context.send.await_args_list)
