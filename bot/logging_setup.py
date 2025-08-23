# bot/logging_setup.py
import sys
from loguru import logger

def setup_logger():
    """Configures the application's logger."""
    logger.remove()  # Remove default handler

    # Console logger for development
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )

    # File logger for production (JSON format)
    logger.add(
        "logs/katana_bot.log",
        level="DEBUG",
        rotation="10 MB",
        compression="zip",
        serialize=True,  # This is the key for JSON logging
        enqueue=True,    # Make logging asynchronous
        backtrace=True,
        diagnose=True
    )

    logger.info("Logger has been configured.")
