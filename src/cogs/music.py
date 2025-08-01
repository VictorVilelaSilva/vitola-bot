from src.commands.ripita import ripitaFunc
from src.commands.silence import silenceFunc, silenceMemberFunc
from src.commands.showQueue import showQueueFunc
from src.commands.youtube import youtubeFunc
from src.commands.tocar import tocarFunc
from discord.ext import commands
import discord


class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Adicionando referência ao bot_instance
        if hasattr(bot, 'bot_instance'):
            self.bot_instance = bot.bot_instance
        else:
            self.bot_instance = bot  # fallback

    @commands.command()
    async def tocar(self, ctx):
        await tocarFunc(ctx, self.bot_instance)
        
    @commands.command()
    async def ripita(self, ctx):
        await ripitaFunc(ctx, self.bot_instance)

    @commands.command(aliases=["yt"])
    async def youtube(self, ctx, link):
        await youtubeFunc(ctx, link, self.bot_instance)

    @commands.command()
    async def showQueue(self, ctx):
        await showQueueFunc(ctx, self.bot_instance)

    @commands.command()
    async def silence(self,ctx,member: discord.Member = None):
        if member is None:
            await silenceFunc(ctx, self.bot_instance)
            return
        await silenceMemberFunc(ctx, self.bot_instance, member)
    
    


async def setup(bot):
    await bot.add_cog(MusicCog(bot))