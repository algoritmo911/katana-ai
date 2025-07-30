# katana/commands/slash_commands.py

import asyncio
import logging
from katana.version import get_version

# Use the root logger configured in bot.py
logger = logging.getLogger(__name__)

async def handle_help(chat_id, args_str, bot, original_message):
    """Handles the /help command."""
    logger.info(f"Handling /help command for chat_id {chat_id}")
    help_text = """\
Доступные команды:
/help — список команд
/version — версия Katana
/status — текущее состояние
/dryrun on|off — включить/выключить dry-run
/reset — сбросить диалог\
"""
    await bot.reply_to(original_message, help_text)

async def handle_version(chat_id, args_str, bot, original_message):
    """Handles the /version command."""
    logger.info(f"Handling /version command for chat_id {chat_id}")
    version_info = get_version()
    await bot.reply_to(original_message, version_info)

async def handle_status(chat_id, args_str, bot, original_message):
    """Handles the /status command."""
    logger.info(f"Handling /status command for chat_id {chat_id}")
    # TODO: Implement uptime and last command tracking
    status_text = "Uptime: 1h 23m\nLast command: /status"
    await bot.reply_to(original_message, status_text)

async def handle_dryrun(chat_id, args_str, bot, original_message):
    """Handles the /dryrun command."""
    logger.info(f"Handling /dryrun command for chat_id {chat_id} with args '{args_str}'")
    if args_str.lower() in ["on", "off"]:
        # TODO: Implement dry-run mode
        await bot.reply_to(original_message, f"Dry-run mode set to {args_str.lower()}")
    else:
        await bot.reply_to(original_message, "Usage: /dryrun on|off")

async def handle_reset(chat_id, args_str, bot, original_message):
    """Handles the /reset command."""
    logger.info(f"Handling /reset command for chat_id {chat_id}")
    # TODO: Implement temporary memory clearing and dialog reset
    await bot.reply_to(original_message, "Dialog reset.")

SLASH_COMMANDS = {
    "/help": handle_help,
    "/version": handle_version,
    "/status": handle_status,
    "/dryrun": handle_dryrun,
    "/reset": handle_reset,
}
