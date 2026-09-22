"""
TokenKeeper — main entry point.
Loads all cogs, starts keepalive for every stored token on ready.
Deploy on Railway: set DISCORD_TOKEN + OWNER_IDS in env vars.
"""

import os
import asyncio
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("TokenKeeper")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN not set in environment")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="tk!", intents=intents)

# attach token manager before cogs load
from utils.token_manager import TokenManager  # noqa: E402
bot.token_manager = TokenManager()


async def load_cogs():
    cog_dir = os.path.join(os.path.dirname(__file__), "commands")
    for fname in os.listdir(cog_dir):
        if fname.endswith(".py") and fname != "__init__.py":
            name = fname[:-3]
            try:
                await bot.load_extension(f"commands.{name}")
                logger.info(f"cog loaded: {name}")
            except Exception as e:
                logger.error(f"cog FAILED {name}: {e}")


@bot.event
async def on_ready():
    logger.info(f"logged in as {bot.user} ({bot.user.id})")
    logger.info(f"tokens in store: {bot.token_manager.get_count()}")

    # ── sync slash commands ────────────────────────────────────────────
    try:
        synced = await bot.tree.sync()
        logger.info(f"synced {len(synced)} slash commands")
    except Exception as e:
        logger.error(f"sync failed: {e}")

    # ── set presence ──────────────────────────────────────────────────
    status_text = os.getenv("BOT_STATUS", "keeping tokens alive")
    activity_key = os.getenv("BOT_ACTIVITY", "watching").lower()
    atype_map = {
        "playing": discord.ActivityType.playing,
        "watching": discord.ActivityType.watching,
        "listening": discord.ActivityType.listening,
        "competing": discord.ActivityType.competing,
    }
    await bot.change_presence(
        activity=discord.Activity(
            type=atype_map.get(activity_key, discord.ActivityType.watching),
            name=status_text,
        )
    )

    # ── auto-start keepalive for all stored tokens ────────────────────
    count = bot.token_manager.get_count()
    if count > 0:
        logger.info(f"launching keepalive for {count} tokens...")
        bot.token_manager.start_all()
        logger.info(f"keepalive running: {bot.token_manager.alive_count()} sessions")
    else:
        logger.info("no tokens stored yet — add some with /add")


async def main():
    async with bot:
        await load_cogs()
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
