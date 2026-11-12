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
        async with self.http_session.get("https://pokeapi.co/api/v2/pokemon?limit=2000") as r:
            listing = await r.json()
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

def build_embed(data, flavor, shiny=False):
    art = data["sprites"]["other"]["official-artwork"]
    image = art["front_shiny"] if shiny else art["front_default"]
    types = ", ".join(t["type"]["name"].title() for t in data["types"])
    stats = "\n".join(f"{s['stat']['name']}: {s['base_stat']}" for s in data["stats"])
    title = f"#{data['id']} {data['name'].title()}" + (" ✨" if shiny else "")

    embed = discord.Embed(title=title, description=flavor)
    if image:
        embed.set_image(url=image)
    embed.add_field(name="Type", value=types)
    embed.add_field(name="Height", value=f"{data['height'] / 10} m")
    embed.add_field(name="Weight", value=f"{data['weight'] / 10} kg")
    embed.add_field(name="Base stats", value=stats, inline=False)
    return embed

class PokemonView(discord.ui.View):
    def __init__(self, data, flavor):
        super().__init__(timeout=120)
        self.data = data
        self.flavor = flavor
        self.shiny = False

    @discord.ui.button(label="Toggle shiny ✨", style=discord.ButtonStyle.primary)
    async def toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.shiny = not self.shiny
        await interaction.response.edit_message(
            embed=build_embed(self.data, self.flavor, self.shiny), view=self
        )

@client.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {client.user}")

@tree.command(name="pokemon", description="Look up a Pokémon")
# NEW: a cooldown. Each person can use this command once every 5 seconds.
# This stops spam and protects your API limits.
@app_commands.checks.cooldown(1, 5.0)
async def pokemon(interaction: discord.Interaction, name: str):
    await interaction.response.defer()
    data = await cached_get(f"https://pokeapi.co/api/v2/pokemon/{name.lower().strip()}")
    if not data:
        await interaction.followup.send(f"Couldn't find '{name}'.")
        return
    species = await cached_get(data["species"]["url"])
    flavor = english_flavor_text(species) if species else "No description available."

    await interaction.followup.send(
        embed=build_embed(data, flavor), view=PokemonView(data, flavor)
    )

@pokemon.autocomplete("name")
async def pokemon_autocomplete(interaction: discord.Interaction, current: str):
    matches = [n for n in client.pokemon_names if current.lower() in n][:25]
    return [app_commands.Choice(name=n, value=n) for n in matches]

# NEW: this runs whenever /pokemon hits an error, including the cooldown.
@pokemon.error
async def pokemon_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    # Was the error caused by the cooldown?
    if isinstance(error, app_commands.CommandOnCooldown):
        # error.retry_after is how many seconds are left. ephemeral=True means
        # only the person who ran the command can see this message.
        await interaction.response.send_message(
            f"Slow down! Try again in {error.retry_after:.1f}s.", ephemeral=True
        )
    else:
        raise error   # any other error: let it show up in the terminal so we can fix it

client.run(os.getenv("DISCORD_TOKEN"))