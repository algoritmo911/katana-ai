import asyncio
from loguru import logger
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from src.katana.core.command_bus import CommandBus
from src.katana.domain.commands import StartCommand, PingCommand
from src.katana.configs.settings import settings

async def _handle_start(message: Message, command_bus: CommandBus):
    """Handler for the /start command."""
    logger.info(f"Received /start from user_id={message.from_user.id}")
    command = StartCommand(
        user_id=message.from_user.id,
        user_name=message.from_user.full_name,
        chat_id=message.chat.id,
    )
    try:
        response = await command_bus.dispatch(command)
        await message.answer(response)
    except Exception as e:
        logger.error(f"Error dispatching StartCommand: {e}")
        await message.answer("An internal error occurred. The team has been notified.")

async def _handle_ping(message: Message, command_bus: CommandBus):
    """Handler for the /ping command."""
    logger.info(f"Received /ping from user_id={message.from_user.id}")
    command = PingCommand(
        user_id=message.from_user.id,
        chat_id=message.chat.id,
    )
    try:
        response = await command_bus.dispatch(command)
        await message.answer(response)
    except Exception as e:
        logger.error(f"Error dispatching PingCommand: {e}")
        await message.answer("An internal error occurred while pinging.")

def setup_telegram_handlers(dp: Dispatcher, command_bus: CommandBus):
    """
    Registers all the necessary Telegram handlers in the dispatcher.

    This function acts as a binder, connecting aiogram's dispatcher
    with the application's command bus.

    Args:
        dp: The aiogram Dispatcher instance.
        command_bus: The application's CommandBus instance.
    """
    # Using a lambda to pass the command_bus to the handler functions.
    # This is a clean way to manage dependencies for handlers in aiogram.
    dp.message.register(
        lambda msg: _handle_start(msg, command_bus),
        Command("start")
    )
    dp.message.register(
        lambda msg: _handle_ping(msg, command_bus),
        Command("ping")
    )
    logger.info("Telegram command handlers registered.")


async def run_telegram_adapter():
    """
    Initializes the Bot and Dispatcher and starts polling for updates.
    This is the main entry point for the Telegram adapter.
    It will be called from the `run.py` script.
    """
    # This function is intended to be called from run.py, which will
    # be responsible for creating and injecting the command_bus.
    # For now, this function is a placeholder for what run.py will do.
    # The actual implementation will be in run.py.
    logger.critical("run_telegram_adapter should not be called directly. It's a placeholder.")
    logger.critical("The application should be started from run.py.")
    pass
