import asyncio
import logging
from contextlib import asynccontextmanager

import discord
from discord import app_commands
from discord.ext import commands

from src.utils import require_voice

log = logging.getLogger(__name__)


def require_voice_check(*permissions):
    async def predicate(ctx):
        require_voice(ctx, *permissions)
        return True

    return commands.check(predicate)


def validate_target(ctx, member, channel):
    if member.guild.id != ctx.guild.id or not member.voice or member.voice.channel != channel:
        raise commands.CheckFailure("O membro precisa estar no mesmo canal de voz que você.")
    if member.bot:
        raise commands.CheckFailure("Não posso aplicar essa ação a bots.")


class VoteView(discord.ui.View):
    def __init__(self, channel, eligible_ids, *, timeout=15):
        super().__init__(timeout=timeout)
        self.channel = channel
        self.eligible_ids = frozenset(eligible_ids)
        self.votes: dict[int, bool] = {}

    def can_vote(self, member):
        return (
            not member.bot
            and member.id in self.eligible_ids
            and member.voice is not None
            and member.voice.channel == self.channel
        )

    async def interaction_check(self, interaction):
        if self.is_finished() or not self.can_vote(interaction.user):
            await interaction.response.send_message(
                "A votação encerrou ou você não é um participante elegível dessa chamada.",
                ephemeral=True,
            )
            return False
        return True

    async def register_vote(self, interaction, remove):
        self.votes[interaction.user.id] = remove
        await interaction.response.send_message(
            "Voto registrado. Você pode alterá-lo até o encerramento.", ephemeral=True
        )

    @discord.ui.button(label="Remover", emoji="👍", style=discord.ButtonStyle.danger)
    async def remove(self, interaction, button):
        await self.register_vote(interaction, True)

    @discord.ui.button(label="Manter", emoji="👎", style=discord.ButtonStyle.secondary)
    async def keep(self, interaction, button):
        await self.register_vote(interaction, False)

    def result(self):
        present = {member.id for member in self.channel.members if self.can_vote(member)}
        yes = sum(vote for user_id, vote in self.votes.items() if user_id in present)
        no = sum(not vote for user_id, vote in self.votes.items() if user_id in present)
        # Strict majority of the original electorate, with at least two supporters.
        required = max(2, len(self.eligible_ids) // 2 + 1)
        return yes, no, required

class ModerationCog(commands.Cog, name="Moderação"):
    def __init__(self, bot):
        self.bot = bot
        self._mute_locks: dict[int, asyncio.Lock] = {}

    @asynccontextmanager
    async def temporary_mute(self, ctx, targets, channel):
        lock = self._mute_locks.setdefault(ctx.guild.id, asyncio.Lock())
        async with lock:
            changed = []
            try:
                if require_voice(ctx, "mute_members") != channel:
                    raise commands.CheckFailure("O autor saiu do canal antes do silenciamento.")
                # Check every target before changing anyone's state.
                for member in targets:
                    validate_target(ctx, member, channel)
                for member in targets:
                    if not member.voice.mute:
                        # Include the attempted edit: a cancelled HTTP request may have reached Discord.
                        changed.append(member)
                        await member.edit(
                            mute=True, reason=f"!silence solicitado por {ctx.author.id}"
                        )
                yield
            finally:
                failed = []
                for member in changed:
                    try:
                        await member.edit(
                            mute=False, reason="Restauração do estado anterior ao !silence"
                        )
                    except Exception:
                        failed.append(str(member.id))
                        log.exception(
                            "Falha ao restaurar mute de %s no servidor %s", member.id, ctx.guild.id
                        )
                if failed:
                    try:
                        await ctx.send(
                            "Não consegui restaurar o áudio destes membros; um moderador precisa verificar: "
                            + ", ".join(failed)
                        )
                    except discord.HTTPException:
                        log.warning(
                            "Não foi possível avisar sobre mutes pendentes no servidor %s",
                            ctx.guild.id,
                        )

    @commands.hybrid_command(
        help="Silencia temporariamente um membro ou os participantes elegíveis da sua chamada."
    )
    @app_commands.describe(member="Membro; deixe vazio para silenciar toda a chamada")
    @commands.guild_only()
    @require_voice_check("mute_members")
    @commands.cooldown(1, 15, commands.BucketType.guild)
    async def silence(self, ctx, member: discord.Member | None = None):
        channel = require_voice(ctx, "mute_members")
        if member is not None:
            validate_target(ctx, member, channel)
            targets = [member]
        else:
            targets = []
            for candidate in channel.members:
                try:
                    validate_target(ctx, candidate, channel)
                except commands.CheckFailure:
                    continue
                targets.append(candidate)
        if not targets:
            raise commands.CheckFailure("Não há membros elegíveis para silenciar nesse canal.")
        music = self.bot.get_cog("Música")
        if music is None:
            raise commands.CheckFailure("O módulo de áudio está indisponível.")
        await music.enqueue_local(
            ctx,
            "silencer_member.mp3" if member else "silencer.mp3",
            effect=lambda: self.temporary_mute(ctx, targets, channel),
        )

    @commands.hybrid_command(
        help="Abre votação de 15s para desconectar um membro da chamada. Exige Mover membros."
    )
    @app_commands.describe(member="Membro que será colocado em votação")
    @commands.guild_only()
    @require_voice_check("move_members")
    @commands.cooldown(1, 30, commands.BucketType.guild)
    @commands.max_concurrency(1, per=commands.BucketType.guild, wait=False)
    async def chato(self, ctx, member: discord.Member):
        channel = require_voice(ctx, "move_members")
        validate_target(ctx, member, channel)
        eligible = {
            candidate.id
            for candidate in channel.members
            if not candidate.bot and candidate.id != member.id
        }
        if len(eligible) < 2:
            raise commands.CheckFailure(
                "São necessários pelo menos dois votantes além do membro indicado."
            )
        view = VoteView(channel, eligible)
        required = max(2, len(eligible) // 2 + 1)
        message = await ctx.send(
            f"Remover {member.display_name} da chamada? Votação de 15s, exige {required} votos a favor. "
            "Somente os participantes atuais, exceto o membro indicado, podem votar.",
            view=view,
        )
        try:
            await view.wait()
        finally:
            view.stop()
            for button in view.children:
                button.disabled = True
            try:
                await message.edit(view=view)
            except discord.HTTPException:
                log.warning("Não foi possível desativar os botões da votação %s", message.id)
        yes, no, required = view.result()
        if yes < required:
            await ctx.send(
                f"O membro permanece na chamada. A favor: {yes}; contra: {no}; necessários: {required}."
            )
            return
        if require_voice(ctx, "move_members") != channel:
            raise commands.CheckFailure("O autor saiu do canal. A remoção foi cancelada.")
        validate_target(ctx, member, channel)
        await member.move_to(
            None, reason=f"Votação !chato iniciada por {ctx.author.id}: {yes} a favor"
        )
        await ctx.send(
            f"{member.display_name} foi removido da chamada. A favor: {yes}; contra: {no}."
        )


async def setup(bot):
    await bot.add_cog(ModerationCog(bot))
