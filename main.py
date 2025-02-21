from src.bot import DiscordBot
from dotenv import load_dotenv

if __name__ == "__main__":
    load_dotenv()

    print("Running bot...")
    DiscordBot().run_discord_bot()
