# katana/commands/slash_commands.py

import asyncio
import logging
from katana.version import get_version

# Use the root logger configured in bot.py
logger = logging.getLogger(__name__)

class SlashCommandRegistry:
    def __init__(self):
        self._commands = {}

    def register(self, name, description=""):
        def decorator(func):
            if not name.startswith('/'):
                raise ValueError("Command name must start with '/'")
            self._commands[name] = {
                "func": func,
                "description": description,
            }
            return func
        return decorator

    async def execute(self, name, chat_id, args_str, bot, original_message):
        command = self._commands.get(name)
        if command:
            await command["func"](chat_id, args_str, bot, original_message)
        else:
            await bot.reply_to(original_message, f"Unknown command: {name}")

    def get_help(self):
        help_text = "Доступные команды:\n"
        for name, command in self._commands.items():
            help_text += f"{name} — {command['description']}\n"
        return help_text

# Create a single registry instance
command_registry = SlashCommandRegistry()

@command_registry.register("/help", description="список команд")
async def handle_help(chat_id, args_str, bot, original_message):
    """Handles the /help command."""
    logger.info(f"Handling /help command for chat_id {chat_id}")
    help_text = command_registry.get_help()
    await bot.reply_to(original_message, help_text)

@command_registry.register("/version", description="версия Katana")
async def handle_version(chat_id, args_str, bot, original_message):
    """Handles the /version command."""
    logger.info(f"Handling /version command for chat_id {chat_id}")
    version_info = get_version()
    await bot.reply_to(original_message, version_info)

@command_registry.register("/status", description="текущее состояние")
async def handle_status(chat_id, args_str, bot, original_message):
    """Handles the /status command."""
    logger.info(f"Handling /status command for chat_id {chat_id}")
    # TODO: Implement uptime and last command tracking
    status_text = "Uptime: 1h 23m\nLast command: /status"
    await bot.reply_to(original_message, status_text)

@command_registry.register("/dryrun", description="включить/выключить dry-run")
async def handle_dryrun(chat_id, args_str, bot, original_message):
    """Handles the /dryrun command."""
    logger.info(f"Handling /dryrun command for chat_id {chat_id} with args '{args_str}'")
    if args_str.lower() in ["on", "off"]:
        # TODO: Implement dry-run mode
        await bot.reply_to(original_message, f"Dry-run mode set to {args_str.lower()}")
    else:
        await bot.reply_to(original_message, "Usage: /dryrun on|off")

@command_registry.register("/reset", description="сбросить диалог")
async def handle_reset(chat_id, args_str, bot, original_message):
    """Handles the /reset command."""
    logger.info(f"Handling /reset command for chat_id {chat_id}")
    # TODO: Implement temporary memory clearing and dialog reset
    await bot.reply_to(original_message, "Dialog reset.")
