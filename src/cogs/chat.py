
from src.commands.comandos import comandosFunc
from src.commands.chato import chatoFunc
from src.commands.gpt import gptFunc
from discord.ext import commands
import discord

class ChatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def chato(self,ctx, member: discord.Member):
        await chatoFunc(ctx, self, member)

    @commands.command()
    async def gpt(self,ctx, message=" "):
        await gptFunc(ctx, self, message)

    @commands.command()
    async def comandos(ctx):
        await comandosFunc(ctx)

async def setup(bot):
    await bot.add_cog(ChatCog(bot))