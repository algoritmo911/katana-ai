"""
This module contains the main logic for the Katana Telegram Bot.

The bot listens for incoming messages, parses them as JSON commands,
validates their structure, and then routes them to the appropriate handlers.
If a command type is not recognized, it is saved to a file for later inspection.
"""
import json
import telebot
from pathlib import Path
from datetime import datetime
from bot_components.handlers.log_event_handler import handle_log_event
from bot_components.handlers.ping_handler import handle_ping
from bot_components.handlers.mind_clearing_handler import (
    handle_mind_clearing,
)
from bot_components.handlers.genesis_handler import handle_genesis

# TODO: Get API token from environment variable or secrets manager
API_TOKEN = "123:dummy_token"  # Placeholder for tests

bot = telebot.TeleBot(API_TOKEN)

# Directory for storing command files
COMMAND_FILE_DIR = Path("commands")
COMMAND_FILE_DIR.mkdir(parents=True, exist_ok=True)


def log_local_bot_event(message):
    """Logs an event to the console."""
    print(f"[BOT EVENT] {datetime.utcnow().isoformat()}: {message}")


# Removed local handle_mind_clearing function


def _validate_command_data(command_data, message):
    """
    Validates the structure and types of the incoming command data.

    Args:
        command_data (dict): The command data to validate.
        message (telebot.types.Message): The message object, used for replying.

    Returns:
        bool: True if the command data is valid, False otherwise.
    """
    chat_id = message.chat.id
    command_text = message.text
    required_fields = {
        "type": str,
        "module": str,
        "args": dict,
        "id": (str, int),  # id can be string or integer
    }

    for field, expected_type in required_fields.items():
        if field not in command_data:
            error_msg = f"Error: Missing required field '{field}'."
            bot.reply_to(message, error_msg)
            log_msg = (
                f"Validation failed for {chat_id}: {error_msg} "
                f"(Command: {command_text})"
            )
            log_local_bot_event(log_msg)
            return False
        # isinstance check for the field's type
        # For 'id', it can be str or int. For others, it's a single type.
        if field == "id":
            if not any(isinstance(command_data[field], t) for t in expected_type):
                type_names = " or ".join(t.__name__ for t in expected_type)
                error_msg = (
                    f"Error: Field '{field}' must be type {type_names}. "
                    f"Got {type(command_data[field]).__name__}."
                )
                bot.reply_to(message, error_msg)
                log_msg = (
                    f"Validation failed for {chat_id}: {error_msg} "
                    f"(Command: {command_text})"
                )
                log_local_bot_event(log_msg)
                return False
        elif not isinstance(command_data[field], expected_type):
            error_msg = (
                f"Error: Field '{field}' must be type "
                f"{expected_type.__name__}."
                f" Got {type(command_data[field]).__name__}."
            )
            bot.reply_to(message, error_msg)
            log_msg = (
                f"Validation failed for {chat_id}: {error_msg} "
                f"(Command: {command_text})"
            )
            log_local_bot_event(log_msg)
            return False
    return True


def _route_command(command_data, message):
    """
    Routes the command to the appropriate handler based on its 'type'.

    Args:
        command_data (dict): The command data.
        message (telebot.types.Message): The message object, used for replying.

    Returns:
        bool: True if a specific handler was found and called, False otherwise.
    """
    chat_id = message.chat.id
    command_type = command_data.get("type")

    if command_type == "log_event":
        handle_log_event(command_data, chat_id, log_local_bot_event)
        bot.reply_to(message, "✅ 'log_event' processed (placeholder).")
        return True
    elif command_type == "ping":
        reply_message = handle_ping(command_data, chat_id, log_local_bot_event)
        bot.reply_to(message, reply_message)
        return True
    elif command_type == "mind_clearing":
        reply_message = handle_mind_clearing(
            command_data, chat_id, log_local_bot_event
        )
        bot.reply_to(message, reply_message)
        return True
    elif command_type == "genesis":
        handle_genesis(command_data, message, bot)
        return True
    return False


def _save_command_to_file(command_data, message):
    """
    Saves unhandled commands to a JSON file for later inspection.

    The file is saved in a directory structure based on the command's 'module'.

    Args:
        command_data (dict): The command data to save.
        message (telebot.types.Message): The message object, used for replying.
    """
    chat_id = message.chat.id
    command_type = command_data.get("type")
    log_local_bot_event(
        f"Command type '{command_type}' not specifically handled, "
        "proceeding with default save."
    )

    timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    command_file_name = f"{timestamp_str}_{chat_id}.json"

    module_name = command_data.get("module", "telegram_general")
    if module_name != "telegram_general":
        module_command_dir = COMMAND_FILE_DIR / f"telegram_mod_{module_name}"
    else:
        module_command_dir = COMMAND_FILE_DIR / "telegram_general"
    module_command_dir.mkdir(parents=True, exist_ok=True)
    command_file_path = module_command_dir / command_file_name

    with open(command_file_path, "w", encoding="utf-8") as f:
        json.dump(command_data, f, ensure_ascii=False, indent=2)

    bot.reply_to(message, f"✅ Command received and saved as `{command_file_path}`.")
    log_local_bot_event(f"Saved command from {chat_id} to {command_file_path}")


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """
    Handles incoming Telegram messages.

    This function serves as the main entry point for message processing.
    It attempts to parse the message as JSON, validates it, and then
    routes it to a specific command handler or saves it if unhandled.
    """
    chat_id = message.chat.id
    command_text = message.text

    log_local_bot_event(f"Received message from {chat_id}: {command_text}")

    try:
        command_data = json.loads(command_text)
    except json.JSONDecodeError:
        bot.reply_to(message, "Error: Invalid JSON format.")
        log_local_bot_event(f"Invalid JSON from {chat_id}: {command_text}")
        return

    if not _validate_command_data(command_data, message):
        return

    if not _route_command(command_data, message):
        _save_command_to_file(command_data, message)


if __name__ == "__main__":
    log_local_bot_event("Bot starting...")
    bot.polling()
    log_local_bot_event("Bot stopped.")
