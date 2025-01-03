
import discord

async def comandosFunc(ctx):
    embed = discord.Embed(
        title="Lista de Comandos",
        description="Aqui estão todos os comandos disponíveis:",
        color=discord.Color.red(),
    )
    embed.add_field(name="!chato <member>", value="Inicia uma votação para expulsar um membro da call.", inline=False)
    embed.add_field(name="!tocar", value="Toca uma música na call.", inline=False)
    embed.add_field(name="!silence [member]", value="Silencia um membro ou todos na call.", inline=False)
    embed.add_field(name="!youtube <link> or !yt <link>", value="Adiciona uma música do youtube na fila de reprodução.", inline=False)
    embed.add_field(name="!yt quit", value="Encerra a fila de reprodução.", inline=False)
    embed.add_field(name="!yt next", value="Pula para a próxima música da fila.", inline=False)
    embed.add_field(name="!showQueue", value="Mostra a fila de reprodução.", inline=False)
    embed.add_field(name="!gpt [message]", value="Inicia uma conversa com o bot GPT.", inline=False)
    await ctx.send(embed=embed)