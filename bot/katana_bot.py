# bot/katana_bot.py
import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from loguru import logger

from bot.logging_setup import setup_logger
from ops.heartbeat import run_heartbeat
from bot.commands import base_commands

# Load environment variables from .env file
load_dotenv()

async def start_bot():
    """Initializes and starts the Katana Telegram Bot."""
    setup_logger()

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.critical("TELEGRAM_BOT_TOKEN is not set!")
        return

    bot = Bot(token=bot_token, parse_mode=ParseMode.HTML)
    dp = Dispatcher()

    # Register command routers
    dp.include_router(base_commands.router)

    # Start the heartbeat as a background task
    heartbeat_task = asyncio.create_task(run_heartbeat())
    logger.info("Heartbeat task created.")

    logger.info("Starting bot polling...")
    await dp.start_polling(bot)

    # This part will be reached upon graceful shutdown
    await heartbeat_task
