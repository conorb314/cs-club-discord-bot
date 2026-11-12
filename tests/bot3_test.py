import os
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
# CHANGED: "name: str" adds an input box to the command. "str" means text.
# Whatever the user types is stored in the variable called name.
async def pokemon(interaction: discord.Interaction, name: str):
    # CHANGED: f"..." is an f-string. Anything in {curly braces} gets replaced
    # with the variable's value.
    await interaction.response.send_message(f"You asked about {name}!")

client.run(os.getenv("DISCORD_TOKEN")) 