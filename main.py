# main.py
import asyncio
from bot.katana_bot import start_bot
from loguru import logger

if __name__ == '__main__':
    try:
        asyncio.run(start_bot())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.exception(f"Critical error at root level: {e}")
