import os
import time                                                          # NEW: lets us check the current time
import aiohttp
import discord
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

client = discord.Client(intents=discord.Intents.default())
tree = app_commands.CommandTree(client)

# NEW: the cache is a dictionary that remembers answers we already fetched.
# Format: web address -> (time we saved it, the data)
cache = {}

# NEW: a "function" is a reusable block of code. This one fetches data from a
# URL, but checks the cache first so we don't repeat requests.
# ttl = "time to live": how many seconds a saved answer stays fresh.
async def cached_get(session, url, ttl=3600):
    # If we already have a recent answer saved, return it right away.
    if url in cache and time.time() - cache[url][0] < ttl:
        return cache[url][1]
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status != 200:
                return None          # None means "it failed"
            data = await r.json()
    except aiohttp.ClientError:
        return None
    # Save the answer and the time, so next time we can skip the request.
    cache[url] = (time.time(), data)
    return data

@client.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {client.user}")

@tree.command(name="pokemon", description="Look up a Pokémon")
async def pokemon(interaction: discord.Interaction, name: str):
    await interaction.response.defer()
    async with aiohttp.ClientSession() as session:
        # CHANGED: all that request code is now one line, using our function.
        data = await cached_get(
            session, f"https://pokeapi.co/api/v2/pokemon/{name.lower().strip()}"
        )
    # CHANGED: if the function gave back None, something went wrong.
    if not data:
        await interaction.followup.send(f"Couldn't find '{name}'.")
        return

    types = ", ".join(t["type"]["name"].title() for t in data["types"])
    stats = "\n".join(f"{s['stat']['name']}: {s['base_stat']}" for s in data["stats"])
    artwork = data["sprites"]["other"]["official-artwork"]["front_default"]

    embed = discord.Embed(title=f"#{data['id']} {data['name'].title()}")
    embed.set_image(url=artwork)
    embed.add_field(name="Type", value=types)
    embed.add_field(name="Height", value=f"{data['height'] / 10} m")
    embed.add_field(name="Weight", value=f"{data['weight'] / 10} kg")
    embed.add_field(name="Base stats", value=stats, inline=False)
    await interaction.followup.send(embed=embed)

client.run(os.getenv("DISCORD_TOKEN"))