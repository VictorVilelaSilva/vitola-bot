from dotenv import load_dotenv
load_dotenv()
from src.DiscordBot import DiscordBot
import asyncio

async def setup():
    bot_instance = DiscordBot()
    bot = bot_instance.init_bot()
    
    # Adicionar referência do bot_instance ao bot
    bot.bot_instance = bot_instance

    # Carregue as extensões de forma assíncrona
    await bot.load_extension("src.cogs.music")
    await bot.load_extension("src.cogs.chat")
    # ...carregue mais Cogs aqui...

    return bot, bot_instance

if __name__ == "__main__":
    # Configurar e iniciar o bot de forma assíncrona
    loop = asyncio.get_event_loop()
    bot, bot_instance = loop.run_until_complete(setup())
    
    print("Running bot...")
    bot.run(bot_instance.TOKEN)
