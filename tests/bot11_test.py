import os
import time
import aiohttp
import discord
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

class PokeClient(discord.Client):
    async def setup_hook(self):
        self.http_session = aiohttp.ClientSession()
        # NEW: at startup, download the list of every Pokémon name ONE time.
        # We need it ready in memory because autocomplete must be fast.
        async with self.http_session.get(
            "https://pokeapi.co/api/v2/pokemon?limit=2000"
        ) as r:
            listing = await r.json()
        # NEW: keep just the names, saved on the bot so commands can use them.
        self.pokemon_names = [p["name"] for p in listing["results"]]

    async def close(self):
        await self.http_session.close()
        await super().close()

client = PokeClient(intents=discord.Intents.default())
tree = app_commands.CommandTree(client)

cache = {}

async def cached_get(url, ttl=3600):
    """Fetch JSON from a URL, reusing a saved copy for `ttl` seconds."""
    if url in cache and time.time() - cache[url][0] < ttl:
        return cache[url][1]
    try:
        async with client.http_session.get(
            url, timeout=aiohttp.ClientTimeout(total=10)
        ) as r:
            if r.status != 200:
                return None
            data = await r.json()
    except aiohttp.ClientError:
        return None
    cache[url] = (time.time(), data)
    return data

def english_flavor_text(species):
    for entry in species["flavor_text_entries"]:
        if entry["language"]["name"] == "en":
            return " ".join(entry["flavor_text"].split())
    return "No description available."

@client.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {client.user}")

@tree.command(name="pokemon", description="Look up a Pokémon")
async def pokemon(interaction: discord.Interaction, name: str):
    await interaction.response.defer()
    data = await cached_get(f"https://pokeapi.co/api/v2/pokemon/{name.lower().strip()}")
    if not data:
        await interaction.followup.send(f"Couldn't find '{name}'.")
        return
    species = await cached_get(data["species"]["url"])

    flavor = english_flavor_text(species) if species else "No description available."
    types = ", ".join(t["type"]["name"].title() for t in data["types"])
    stats = "\n".join(f"{s['stat']['name']}: {s['base_stat']}" for s in data["stats"])
    artwork = data["sprites"]["other"]["official-artwork"]["front_default"]

    embed = discord.Embed(title=f"#{data['id']} {data['name'].title()}", description=flavor)
    embed.set_image(url=artwork)
    embed.add_field(name="Type", value=types)
    embed.add_field(name="Height", value=f"{data['height'] / 10} m")
    embed.add_field(name="Weight", value=f"{data['weight'] / 10} kg")
    embed.add_field(name="Base stats", value=stats, inline=False)
    await interaction.followup.send(embed=embed)

# NEW: this function runs while the user is still typing in the "name" box.
# "current" is whatever they've typed so far.
@pokemon.autocomplete("name")
async def pokemon_autocomplete(interaction: discord.Interaction, current: str):
    # Keep names that contain the typed text. [:25] keeps only the first 25,
    # because Discord allows at most 25 suggestions.
    matches = [n for n in client.pokemon_names if current.lower() in n][:25]
    # Turn each name into a Choice, the format Discord expects for suggestions.
    return [app_commands.Choice(name=n, value=n) for n in matches]

client.run(os.getenv("DISCORD_TOKEN"))