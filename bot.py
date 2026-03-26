import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import openai

print("Starting bot...")
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("Error: DISCORD_TOKEN not found in environment variables")
    exit(1)

print("Discord token found, initializing bot...")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Load all cogs from the cogs/ folder
async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"Loaded cog: {filename[:-3]}")
            except Exception as e:
                print(f"Failed to load cog {filename[:-3]}: {e}")

@bot.event
async def on_ready():
    print(f"{bot.user} is serving democracy 💅")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    # Set status to 'Virginia Politics'
    activity = discord.Activity(type=discord.ActivityType.custom, name="Virginia Politics")
    await bot.change_presence(status=discord.Status.online, activity=activity)

mod_channel_id = os.getenv("MOD_CHANNEL_ID")
if mod_channel_id is not None:
    try:
        mod_channel_id = int(mod_channel_id)
    except ValueError:
        print("Warning: MOD_CHANNEL_ID is not a valid integer")
        mod_channel_id = None
else:
    print("Warning: MOD_CHANNEL_ID not set in environment variables.")

async def main():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
