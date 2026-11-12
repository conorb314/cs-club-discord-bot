import os
import aiohttp
import discord
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

client = discord.Client(intents=discord.Intents.default())
tree = app_commands.CommandTree(client)

@client.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {client.user}")

@tree.command(name="pokemon", description="Look up a Pokémon")
async def pokemon(interaction: discord.Interaction, name: str):
    # NEW: Discord only gives us 3 seconds to reply. defer() says "I'm working
    # on it!" (users see "Bot is thinking...") and gives us more time.
    await interaction.response.defer()

    url = f"https://pokeapi.co/api/v2/pokemon/{name.lower().strip()}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 404:
                    # CHANGED: after defer(), we reply with followup.send()
                    # instead of response.send_message().
                    await interaction.followup.send(f"No Pokémon called '{name}'.")
                    return
                if r.status != 200:
                    await interaction.followup.send(f"API error ({r.status}).")
                    return
                data = await r.json()
    except aiohttp.ClientError:
        await interaction.followup.send("Couldn't reach the API.")
        return

    # NEW: an "embed" is a fancy message box with a title, fields, and images.
    embed = discord.Embed(title=f"#{data['id']} {data['name'].title()}")
    # A thumbnail is a small picture in the corner of the embed.
    embed.set_thumbnail(url=data["sprites"]["front_default"])
    # Fields are labeled pieces of information.
    embed.add_field(name="Height", value=f"{data['height'] / 10} m")
    await interaction.followup.send(embed=embed)

client.run(os.getenv("DISCORD_TOKEN"))