
import discord
import asyncio

async def chatoFunc(ctx, bot, member: discord.Member):
    if member.voice is None:
        await ctx.send(f"{member.name} não está em uma call.")
        return

    await ctx.send(
        f"Vote no membro {member.name} para ser expulso da call. Reaja com 👍 para tirar ele da call ou com 👎 para não retirar ele da call"
    )
    votacao_msg = await ctx.send("Vote aqui!")
    await asyncio.gather(
        votacao_msg.add_reaction("👍"),
        votacao_msg.add_reaction("👎")
    )

    tempo_votacao = 6
    await asyncio.sleep(tempo_votacao)

    await ctx.send("Votação encerrada!")
    votacao_msg = await ctx.fetch_message(votacao_msg.id)

    reacoes = votacao_msg.reactions
    votos_positivos = 0
    votos_negativos = 0
    for reacao in reacoes:
        if reacao.emoji == "👍":
            votos_positivos = reacao.count
        elif reacao.emoji == "👎":
            votos_negativos = reacao.count

    if votos_positivos > votos_negativos:
        try:
            await asyncio.gather(
                member.move_to(None),
                ctx.send(
                    f"{member.name} foi removido da call com {votos_positivos} votos a favor e {votos_negativos} votos contra."
                ),
            )
        except Exception as e:
            await ctx.send(
                f"Não foi possível remover {member.name} da call. Erro: {e}"
            )
    else:
        await ctx.send(
            f"{member.name} permanecerá na call. Votos a favor: {votos_positivos}, votos contra: {votos_negativos}"
        )