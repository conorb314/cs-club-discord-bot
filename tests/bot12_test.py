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

# NEW: we moved all the embed-building code into its own function, because
# now two places need it: the command AND the button.
# shiny=False is a default: if you don't say otherwise, it's the normal version.
def build_embed(data, flavor, shiny=False):
    art = data["sprites"]["other"]["official-artwork"]
    # Pick the shiny picture or the normal one depending on "shiny".
    image = art["front_shiny"] if shiny else art["front_default"]
    types = ", ".join(t["type"]["name"].title() for t in data["types"])
    stats = "\n".join(f"{s['stat']['name']}: {s['base_stat']}" for s in data["stats"])
    # Add a sparkle emoji to the title when shiny.
    title = f"#{data['id']} {data['name'].title()}" + (" ✨" if shiny else "")

    embed = discord.Embed(title=title, description=flavor)
    if image:   # some Pokémon have no shiny picture, so check first
        embed.set_image(url=image)
    embed.add_field(name="Type", value=types)
    embed.add_field(name="Height", value=f"{data['height'] / 10} m")
    embed.add_field(name="Weight", value=f"{data['weight'] / 10} kg")
    embed.add_field(name="Base stats", value=stats, inline=False)
    return embed    # hand the finished embed back to whoever called this function

# NEW: a "View" is a container that holds buttons under a message.
class PokemonView(discord.ui.View):
    # __init__ runs when we create a new PokemonView. It saves the info
    # the button will need later.
    def __init__(self, data, flavor):
        super().__init__(timeout=120)   # buttons stop working after 2 minutes
        self.data = data
        self.flavor = flavor
        self.shiny = False              # starts as the normal version

    # This decorator turns the function below into a clickable button.
    @discord.ui.button(label="Toggle shiny ✨", style=discord.ButtonStyle.primary)
    async def toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.shiny = not self.shiny     # flip True <-> False
        # Edit the existing message with a rebuilt embed instead of sending a new one.
        await interaction.response.edit_message(
            embed=build_embed(self.data, self.flavor, self.shiny), view=self
        )

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

    # CHANGED: build the embed with our function, and attach the button view.
    await interaction.followup.send(
        embed=build_embed(data, flavor), view=PokemonView(data, flavor)
    )

@pokemon.autocomplete("name")
async def pokemon_autocomplete(interaction: discord.Interaction, current: str):
    matches = [n for n in client.pokemon_names if current.lower() in n][:25]
    return [app_commands.Choice(name=n, value=n) for n in matches]

client.run(os.getenv("DISCORD_TOKEN"))