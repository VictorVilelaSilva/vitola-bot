import discord
from discord.ext import commands
from dotenv import load_dotenv
import comandsFunctions
import asyncio
import os
from datetime import timedelta

async def chato(ctx):
        if ctx.guild is None:
            await ctx.send("Esse comando só pode ser usado em servidores.")
            return

        # Verifica se o autor da mensagem tem permissão para mover membros
        if not ctx.author.guild_permissions.move_members:
            await ctx.send("Voce não tem permissão para usar esse comando.")
            return

        # Pegar o primeiro membro mencionado na mensagem
        if len(ctx.message.mentions) == 0:
            await ctx.send("Mencione um usuário para ser chutado.")
            return
        user = ctx.message.mentions[0]

        # Inicia a votação
        await ctx.send(f"Vote no membro {user.mention} para ser chutado. Reaja com 👍 para votar.")

        # adicion uma reção na mensagem digita da pelo bot
        await ctx.message.add_reaction("👍")

        # verifica se a reação é correta
        def check(reaction, user):
            return str(reaction.emoji) == "👍" and reaction.message == ctx.message

        # Espera por reações por 60 segundos
        try:
            reaction, _ = await client.wait_for("reaction_add", timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send("Votação encerrada. Não houve votos suficientes para chutar.")
            return

        # Check if there are enough votes to kick
        if reaction.count > 2:
            # Move o usuario marcado para para fora do nacal de voz
            member = ctx.guild.get_member(user.id)
            await member.move_to(None)
        else:
            await ctx.send("Não houve votos dropar do canal")