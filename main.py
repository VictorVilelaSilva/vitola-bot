from dotenv import load_dotenv
load_dotenv()
from src.DiscordBot import DiscordBot
import asyncio

async def setup_extensions(bot):
    # Carregue as extensões de forma assíncrona
    await bot.load_extension("src.cogs.music")
    await bot.load_extension("src.cogs.chat")

def main():
    bot_instance = DiscordBot()
    bot = bot_instance.init_bot()
    
    bot.bot_instance = bot_instance
    
    asyncio.run(setup_extensions(bot))
    
    print("Running bot...")
    bot.run(bot_instance.TOKEN)

if __name__ == "__main__":
    main()
