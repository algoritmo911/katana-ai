# bot/commands/base_commands.py
from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from loguru import logger

router = Router()

@router.message(CommandStart())
async def handle_start(message: types.Message):
    """Handler for the /start command."""
    user_name = message.from_user.full_name
    logger.info(f"User {user_name} (ID: {message.from_user.id}) started the bot.")
    await message.answer(f"Привет, {user_name}!\nKatana к вашим услугам.")

@router.message(Command(commands=["ping"]))
async def handle_ping(message: types.Message):
    """Handler for the /ping command."""
    logger.info(f"Received /ping from user {message.from_user.id}.")
    await message.answer("pong")
