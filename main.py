from dotenv import load_dotenv
load_dotenv()
from src.bot import DiscordBot

if __name__ == "__main__":

    print("Running bot...")
    DiscordBot().run_discord_bot()
