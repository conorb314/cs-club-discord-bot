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
    await interaction.response.defer()
    url = f"https://pokeapi.co/api/v2/pokemon/{name.lower().strip()}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 404:
                    await interaction.followup.send(f"No Pokémon called '{name}'.")
                    return
                if r.status != 200:
                    await interaction.followup.send(f"API error ({r.status}).")
                    return
                data = await r.json()
    except aiohttp.ClientError:
        await interaction.followup.send("Couldn't reach the API.")
        return

    # NEW: a Pokémon can have several types, stored as a list in the data.
    # This loops over the list, grabs each type's name, and joins them with commas.
    # Example result: "Fire, Flying"
    types = ", ".join(t["type"]["name"].title() for t in data["types"])

    # NEW: same idea for stats. Each stat becomes a line like "hp: 35",
    # and "\n" puts each one on a new line.
    stats = "\n".join(f"{s['stat']['name']}: {s['base_stat']}" for s in data["stats"])

    # NEW: this digs through layers of data ("nested" data) to find a big picture.
    artwork = data["sprites"]["other"]["official-artwork"]["front_default"]

    embed = discord.Embed(title=f"#{data['id']} {data['name'].title()}")
    embed.set_image(url=artwork)                                    # CHANGED: big image instead of a thumbnail
    embed.add_field(name="Type", value=types)                       # NEW
    embed.add_field(name="Height", value=f"{data['height'] / 10} m")
    embed.add_field(name="Weight", value=f"{data['weight'] / 10} kg")   # NEW
    # inline=False puts this field on its own row instead of beside others.
    embed.add_field(name="Base stats", value=stats, inline=False)   # NEW
    await interaction.followup.send(embed=embed)

client.run(os.getenv("DISCORD_TOKEN"))