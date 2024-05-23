import discord
from discord.ext import commands
from dotenv import load_dotenv
import responses
import asyncio
import os

async def send_message(message, return_message, is_private):
    try:
        await message.channel.send(return_message) if is_private else await message.channel.send(return_message)
    except Exception as e:
        print(e)


def run_discord_bot():
    load_dotenv()
    TOKEN = os.getenv('DISCORD_TOKEN')

    if TOKEN is None:
        print("Please set the DISCORD_TOKEN environment variable.")
        exit(1)
    intents = discord.Intents.default()
    intents.message_content = True
    
    PREFIX = '!meuBot'
    # client = discord.Client(intents=intents)
    client = commands.Bot(command_prefix = PREFIX, intents=intents)

    @client.event
    async def on_ready():
        print(f'Estrou on the line {client.user}')
    
    @client.command()
    async def ping(ctx):
        print('Ping command triggered')
        await ctx.send("Pong!")
    
    @client.command()
    async def chato(ctx):
        print('Chato command entered')
        # Check if the command was used in a guild
        if ctx.guild is None:
            await ctx.send("This command can only be used in a server.")
            return

        # Check if the user has the necessary permissions to kick members
        if not ctx.author.guild_permissions.kick_members:
            await ctx.send("You don't have permission to kick members.")
            return

        # Get the mentioned user
        if len(ctx.message.mentions) == 0:
            await ctx.send("Please mention a user to kick.")
            return
        user = ctx.message.mentions[0]

        # Start the vote
        await ctx.send(f"Voting to kick {user.mention} has started. React with 👍 to vote.")

        # Add reactions for voting
        await ctx.message.add_reaction("👍")

        # Define the check function for the reaction event
        def check(reaction, user):
            return str(reaction.emoji) == "👍" and reaction.message == ctx.message

        # Wait for reactions
        try:
            reaction, _ = await client.wait_for("reaction_add", timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send("Voting has ended. Not enough votes to kick.")
            return

        # Check if there are enough votes to kick
        if reaction.count > 1:
            # Kick the user
            await user.kick(reason="Voted out")
            await ctx.send(f"{user.mention} has been kicked.")
        else:
            await ctx.send("Voting has ended. Not enough votes to kick.")

    @client.event
    async def on_message(message):
        if message.author == client.user:
            return
        
        username = str(message.author)

        user_message = str(message.content)
        
        channel = str(message.channel)

        print(f'{username} in {channel} said: {user_message}')


        if username == 'chaul0205':
            await message.add_reaction('<:Chaul:1243037858907029534>')
        
        await client.process_commands(message)
            # await send_message(message, f'{message.author.mention} <:astral:858408913317134336>', False)
        #     for voice_channel in message.guild.voice_channels:
        #         for member in voice_channel.members:
        #             if member.name == 'vitolaapenas':
        #                 await message.channel.send(':astral: @vitolaapenas :astral:')
        #                 await member.move_to(None)
        #                 break

    client.run(TOKEN)
