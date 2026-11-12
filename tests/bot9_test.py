import os
import time
import aiohttp
import discord
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

client = discord.Client(intents=discord.Intents.default())
tree = app_commands.CommandTree(client)

cache = {}

async def cached_get(session, url, ttl=3600):
    """Fetch JSON from a URL, reusing a saved copy for `ttl` seconds."""
    if url in cache and time.time() - cache[url][0] < ttl:
        return cache[url][1]
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status != 200:
                return None
            data = await r.json()
    except aiohttp.ClientError:
        return None
    cache[url] = (time.time(), data)
    return data

# NEW: another helper. The species data has descriptions in many languages.
# This loops through them and returns the first English one.
def english_flavor_text(species):
    for entry in species["flavor_text_entries"]:
        if entry["language"]["name"] == "en":
            # The raw text has weird line breaks. split() + join() tidies
            # them into normal spaces.
            return " ".join(entry["flavor_text"].split())
    return "No description available."

@client.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {client.user}")

@tree.command(name="pokemon", description="Look up a Pokémon")
async def pokemon(interaction: discord.Interaction, name: str):
    await interaction.response.defer()
    async with aiohttp.ClientSession() as session:
        data = await cached_get(
            session, f"https://pokeapi.co/api/v2/pokemon/{name.lower().strip()}"
        )
        if not data:
            await interaction.followup.send(f"Couldn't find '{name}'.")
            return
        # NEW: the first response contained a link to more info (the species).
        # We use that link for a second request. This is called "chaining."
        species = await cached_get(session, data["species"]["url"])

    # NEW: if the second request failed, use a backup message instead of crashing.
    flavor = english_flavor_text(species) if species else "No description available."
    types = ", ".join(t["type"]["name"].title() for t in data["types"])
    stats = "\n".join(f"{s['stat']['name']}: {s['base_stat']}" for s in data["stats"])
    artwork = data["sprites"]["other"]["official-artwork"]["front_default"]

    # CHANGED: description= puts the text under the embed's title.
    embed = discord.Embed(title=f"#{data['id']} {data['name'].title()}", description=flavor)
    embed.set_image(url=artwork)
    embed.add_field(name="Type", value=types)
    embed.add_field(name="Height", value=f"{data['height'] / 10} m")
    embed.add_field(name="Weight", value=f"{data['weight'] / 10} kg")
    embed.add_field(name="Base stats", value=stats, inline=False)
    await interaction.followup.send(embed=embed)

client.run(os.getenv("DISCORD_TOKEN"))