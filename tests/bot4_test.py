import os
import aiohttp                                                # NEW: library for making web requests
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
    # NEW: a "session" is like opening a browser so we can visit web addresses.
    # "async with" opens it and closes it automatically when we're done.
    async with aiohttp.ClientSession() as session:
        # NEW: send a GET request (a "please give me data" message) to PokeAPI.
        # .lower() makes the name lowercase because the API needs lowercase.
        async with session.get(f"https://pokeapi.co/api/v2/pokemon/{name.lower()}") as r:
            # NEW: the API answers in JSON, a text format that Python turns
            # into a dictionary (data we can look things up in by name).
            data = await r.json()

    # CHANGED: pull specific fields out of the data, like data['id'].
    # Heights from the API are in decimeters, so dividing by 10 gives meters.
    await interaction.response.send_message(
        f"#{data['id']} {data['name'].title()}, height {data['height'] / 10} m"
    )

client.run(os.getenv("DISCORD_TOKEN"))