import os
import discord
from discord import app_commands                              # NEW: tools for slash commands
from dotenv import load_dotenv

load_dotenv()

client = discord.Client(intents=discord.Intents.default())

# NEW: the "tree" is the list of all our slash commands.
tree = app_commands.CommandTree(client)

# NEW: this function runs automatically once the bot has connected.
# "async" means the function is allowed to wait for things (like the network)
# without freezing the whole bot.
@client.event
async def on_ready():
    # Send our command list to Discord. Without this, /pokemon never appears.
    # "await" means "wait here until this finishes."
    await tree.sync()
    print(f"Logged in as {client.user}")   # shows in your terminal so you know it worked

# NEW: this creates the slash command /pokemon.
# The text in description shows up in Discord's command menu.
@tree.command(name="pokemon", description="Look up a Pokémon")
async def pokemon(interaction: discord.Interaction):
    # "interaction" represents the user running the command.
    # We use it to send a reply back to them.
    await interaction.response.send_message("Pikachu is an Electric-type!")

client.run(os.getenv("DISCORD_TOKEN"))