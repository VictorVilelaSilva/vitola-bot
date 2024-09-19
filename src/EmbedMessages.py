import discord


def ytEmbed(YtTitle, url, thumbnail):
    embed = discord.Embed(
        title=YtTitle,
        color=discord.Color.red(),
    )
    embed.add_field(name="Link", value=url, inline=False)
    embed.set_image(url=thumbnail)
    return embed


def showYtQueue(QUEUE):
    embed = discord.Embed(
        title="Fila de reprodução",
        color=discord.Color.red(),
    )
    for i, item in enumerate(QUEUE):
        embed.add_field(
            name=f"{i+1} - {item['title']}", value=item["link"], inline=False
        )
    return embed
