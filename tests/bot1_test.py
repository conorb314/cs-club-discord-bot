# "import" loads code that other people wrote so we can use it.
import os                            # lets us read settings like our secret token
import discord                       # the library that talks to Discord for us
from dotenv import load_dotenv       # reads secrets from the .env file

# Read the .env file so the token is available to our program.
load_dotenv()

# Create the bot. "Intents" tell Discord which kinds of events we want to hear
# about. default() is the normal, safe set.
client = discord.Client(intents=discord.Intents.default())

# Log in with our token and start running. The program stays on this line
# until you stop it. When it stops, the bot goes offline.
client.run(os.getenv("DISCORD_TOKEN"))