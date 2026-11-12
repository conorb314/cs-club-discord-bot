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
    # CHANGED: .strip() removes accidental spaces around what the user typed.
    url = f"https://pokeapi.co/api/v2/pokemon/{name.lower().strip()}"

    # NEW: "try" means "attempt this, and if the internet breaks, don't crash."
    try:
        async with aiohttp.ClientSession() as session:
            # CHANGED: timeout = give up after 10 seconds instead of waiting forever.
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                # NEW: r.status is a number telling us how the request went.
                # 404 means "not found" (the Pokémon doesn't exist).
                if r.status == 404:
                    await interaction.response.send_message(f"No Pokémon called '{name}'.")
                    return   # stop here, don't run the rest of the function
                # 200 means success. Anything else is some other kind of error.
                if r.status != 200:
                    await interaction.response.send_message(f"API error ({r.status}).")
                    return
                data = await r.json()
    # NEW: "except" runs if the "try" part failed (for example, no internet).
    except aiohttp.ClientError:
        await interaction.response.send_message("Couldn't reach the API.")
        return

    await interaction.response.send_message(
        f"#{data['id']} {data['name'].title()}, height {data['height'] / 10} m"
    )

client.run(os.getenv("DISCORD_TOKEN"))