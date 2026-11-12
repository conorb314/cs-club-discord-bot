import os
import time
import aiohttp
import discord
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

# NEW: a "class" is a blueprint. We're making our own version of the bot that
# does extra setup work. "(discord.Client)" means "start from the normal bot
# and add to it."
class PokeClient(discord.Client):
    # setup_hook runs ONCE, right when the bot starts up.
    async def setup_hook(self):
        # Create one web session and keep it on the bot, so every command can
        # reuse it instead of opening a new one each time.
        self.http_session = aiohttp.ClientSession()

    # close runs when the bot shuts down. We tidy up our session first.
    async def close(self):
        await self.http_session.close()
        await super().close()    # then let the normal bot shut down too

client = PokeClient(intents=discord.Intents.default())     # CHANGED: use our new bot class
tree = app_commands.CommandTree(client)

cache = {}

# CHANGED: no "session" argument anymore. We use client.http_session instead.
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
    # CHANGED: no more "async with aiohttp.ClientSession()" block. Much cleaner!
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

client.run(os.getenv("DISCORD_TOKEN"))