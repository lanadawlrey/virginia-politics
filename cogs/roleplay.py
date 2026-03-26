import discord
from discord import app_commands
from discord.ext import commands
import openai
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
else:
    print("Warning: OPENAI_API_KEY not set")

class Roleplay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="news", description="Generate an AI-powered news coverage summary of current events in the community.")
    @app_commands.describe(
        user_prompt="Describe the focus or angle for the news coverage (e.g. 'Legislative debates', 'Public reaction to new bill'). Leave blank for general coverage."
    )
    async def news(self, interaction: discord.Interaction, user_prompt: str = ""):
        await interaction.response.defer(thinking=True)
        channel_ids = [
            1486599364381118575, 1486599518387572876, 1486599541061980303, 1486599561882632384,
            1486597927953764422, ]
        all_messages = []
        for cid in channel_ids:
            channel = interaction.guild.get_channel(cid)
            if channel and isinstance(channel, discord.TextChannel):
                try:
                    async for msg in channel.history(limit=20, oldest_first=False):
                        # Add plain text content
                        if msg.content:
                            all_messages.append(f"{msg.author.display_name}: {msg.content}")
                        # Add embed content
                        for embed in msg.embeds:
                            embed_parts = []
                            if embed.title:
                                embed_parts.append(f"[EMBED TITLE] {embed.title}")
                            if embed.description:
                                embed_parts.append(f"[EMBED DESC] {embed.description}")
                            for field in getattr(embed, 'fields', []):
                                embed_parts.append(f"[EMBED FIELD] {field.name}: {field.value}")
                            if embed_parts:
                                all_messages.append(f"{msg.author.display_name}: " + " ".join(embed_parts))
                except Exception as e:
                    all_messages.append(f"[Could not fetch messages from {cid}: {e}]")
        combined_chats = '\n'.join(all_messages[-100:])
        game_context = {
            "recent_chats": combined_chats
        }
        options = {
            "tone": "serious and journalistic",
            "model": "gpt-5.4-mini-2026-03-17",
            "max_tokens": 600,
            "temperature": 0.7
        }
        embed = await self.generate_news_coverage(game_context, options, user_prompt)
        await interaction.followup.send(embed=embed)

    async def generate_news_coverage(self, game_context: dict, options: dict, user_prompt: str) -> discord.Embed:
        prompt = f"""
You are an experienced news journalist reporting for a major state news agency in a simulation of the State of Virginia. The year is 2026, and your coverage should reflect the political climate, issues, and personalities of that time.

Important: Never mention the name 'Virginia Politics' in your article. Always refer to the simulation as the Virginia States, Virginia, or the state. Do not reference the existence of a simulation or community name.

Your job is to write a public news article summarizing the most important, dramatic, or controversial current events and discussions happening in the US, based on the latest chat logs provided. If the user has provided a focus or angle, tailor your coverage accordingly. Your tone should be serious, factual, and engaging, as if writing for a respected national newspaper. Avoid roleplay event prompts—focus on news coverage and public reporting.

User's requested focus: {user_prompt if user_prompt else 'General news coverage'}

Recent community discussions:
{game_context.get('recent_chats', 'N/A')}

Write a headline and a concise, informative news article for the State of Virginia.
"""
        try:
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = await self.bot.loop.run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model=options.get('model', 'gpt-5.4-mini-2026-03-17'),
                    messages=[{"role": "system", "content": prompt}],
                    max_tokens=options.get('max_tokens', 600),
                    temperature=options.get('temperature', 0.7),
                )
            )
            news_text = response.choices[0].message.content.strip()
        except Exception as e:
            news_text = f"⚠️ Error generating news: {e}"
        embed = discord.Embed(
            title="📰 Virginia News",
            description=news_text,
            color=0x3498db
        )
        return embed

async def setup(bot):
    await bot.add_cog(Roleplay(bot))
