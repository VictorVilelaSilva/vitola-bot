
import discord
from commands.helpers.EmbedMessages import showYtQueue

async def showQueueFunc(ctx, bot):
    if len(bot.QUEUE) == 0:
        embed = discord.Embed(
            title="Fila de reprodução",
            description="Nenhuma música na fila.",
            color=discord.Color.red(),
        )
        return await ctx.send(embed=embed)
    await ctx.send(embed=showYtQueue(bot.QUEUE))