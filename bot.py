import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import openai

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Load all cogs from the cogs/ folder
async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")

@bot.event
async def on_ready():
    print(f"{bot.user} is serving democracy 💅")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    # Set status to 'Watching over Democracy' (no emoji)
    activity = discord.Activity(type=discord.ActivityType.watching, name="over Democracy")
    await bot.change_presence(status=discord.Status.online, activity=activity)

mod_channel_id = os.getenv("MOD_CHANNEL_ID")
if mod_channel_id is not None:
    mod_channel_id = int(mod_channel_id)
else:
    print("Warning: MOD_CHANNEL_ID not set in .env file.")

async def main():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
