import asyncio
from loguru import logger
from aiogram import Bot, Dispatcher

from src.katana.configs.settings import settings
from src.katana.configs.logging_config import setup_logger
from src.katana.core.command_bus import CommandBus
from src.katana.core.handlers import StartCommandHandler, PingCommandHandler
from src.katana.domain.commands import StartCommand, PingCommand
from src.katana.adapters.telegram_adapter import setup_telegram_handlers

# The memory service is not actively used by the handlers yet,
# but it's here to show how dependencies would be managed.
# from src.katana.services.memory import AbstractMemoryService
# from src.katana.infrastructure.redis_memory import RedisMemoryService


async def main():
    """
    The main composition root of the application.

    This function is responsible for:
    1. Setting up logging and configuration.
    2. Instantiating all major components (services, command bus, handlers).
    3. "Wiring" the components together (Dependency Injection).
    4. Starting the primary adapter (Telegram polling).
    """
    # 1. Initial Setup
    setup_logger()
    logger.info("--- Katana Bot Initializing ---")
    logger.debug(f"Settings loaded: LOG_LEVEL={settings.log_level}")

    # 2. Dependency/Service Initialization
    # When handlers need services, they would be created here.
    # For example:
    # memory_service: AbstractMemoryService = RedisMemoryService()

    # 3. Core Components Initialization
    command_bus = CommandBus()

    # 4. Handler Initialization and Registration
    # Dependencies are injected into handlers here.
    # e.g., start_handler = StartCommandHandler(memory_service=memory_service)
    start_handler = StartCommandHandler()
    ping_handler = PingCommandHandler()

    command_bus.register(StartCommand, start_handler)
    command_bus.register(PingCommand, ping_handler)
    logger.info("Command bus and handlers are configured.")

    # 5. Adapter Initialization
    bot = Bot(token=settings.telegram_token)
    dp = Dispatcher()

    # The adapter is given the command bus it needs to function.
    setup_telegram_handlers(dp, command_bus)
    logger.info("Telegram adapter configured.")

    # 6. Start Application
    logger.info("Initialization complete. Starting polling...")
    try:
        # Good practice: remove any existing webhook and drop pending updates.
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        logger.info("--- Katana Bot Shutting Down ---")
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped manually.")
    except Exception as e:
        # This will catch any exceptions during the startup phase.
        logger.opt(exception=True).critical(f"A critical error occurred during application startup: {e}")
        # Exit with a non-zero status code to indicate failure.
        exit(1)
