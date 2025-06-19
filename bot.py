import telebot
import json
import os
from pathlib import Path
from datetime import datetime

# TODO: Get API token from environment variable or secrets manager
API_TOKEN = 'YOUR_API_TOKEN'

bot = telebot.TeleBot(API_TOKEN)

# Directory for storing command files
COMMAND_FILE_DIR = Path('commands')
COMMAND_FILE_DIR.mkdir(parents=True, exist_ok=True)

def log_local_bot_event(message):
    """Logs an event to the console."""
    print(f"[BOT EVENT] {datetime.utcnow().isoformat()}: {message}")

def handle_log_event(command_data, chat_id):
    """Placeholder for handling 'log_event' commands."""
    log_local_bot_event(f"handle_log_event called for chat_id {chat_id} with data: {command_data}")
    # Actual implementation for log_event will go here
    # bot.reply_to(message, "✅ 'log_event' received (placeholder).") # TODO: Add reply mechanism

def handle_mind_clearing(command_data, chat_id):
    """Placeholder for handling 'mind_clearing' commands."""
    log_local_bot_event(f"handle_mind_clearing called for chat_id {chat_id} with data: {command_data}")
    # Actual implementation for mind_clearing will go here
    # bot.reply_to(message, "✅ 'mind_clearing' received (placeholder).") # TODO: Add reply mechanism

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Handles incoming messages."""
    chat_id = message.chat.id
    command_text = message.text

    log_local_bot_event(f"Received message from {chat_id}: {command_text}")

    try:
        command_data = json.loads(command_text)
    except json.JSONDecodeError:
        bot.reply_to(message, "Error: Invalid JSON format.")
        log_local_bot_event(f"Invalid JSON from {chat_id}: {command_text}")
        return

    # Validate command_data fields
    required_fields = {
        "type": str,
        "module": str,
        "args": dict,
        "id": (str, int)  # id can be string or integer
    }

    for field, expected_type in required_fields.items():
        if field not in command_data:
            error_msg = f"Error: Missing required field '{field}'."
            bot.reply_to(message, error_msg)
            log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text})")
            return
        # isinstance check for the field's type
        # For 'id', it can be str or int. For others, it's a single type.
        if field == "id":
            if not any(isinstance(command_data[field], t) for t in expected_type):
                error_msg = f"Error: Field '{field}' must be type {' or '.join(t.__name__ for t in expected_type)}. Got {type(command_data[field]).__name__}."
                bot.reply_to(message, error_msg)
                log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text})")
                return
        elif not isinstance(command_data[field], expected_type):
            error_msg = f"Error: Field '{field}' must be type {expected_type.__name__}. Got {type(command_data[field]).__name__}."
            bot.reply_to(message, error_msg)
            log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text})")
            return

    # Command routing based on 'type'
    command_type = command_data.get("type")

    if command_type == "log_event":
        handle_log_event(command_data, chat_id)
        bot.reply_to(message, "✅ 'log_event' processed (placeholder).")
        return
    elif command_type == "mind_clearing":
        handle_mind_clearing(command_data, chat_id)
        bot.reply_to(message, "✅ 'mind_clearing' processed (placeholder).")
        return

    # If type is not matched, proceed with default behavior (saving)
    log_local_bot_event(f"Command type '{command_type}' not specifically handled, proceeding with default save.")

    # Save the command to a file
    timestamp_str = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
    command_file_name = f"{timestamp_str}_{chat_id}.json"

    module_name = command_data.get('module', 'telegram_general')
    module_command_dir = COMMAND_FILE_DIR / f"telegram_mod_{module_name}" if module_name != 'telegram_general' else COMMAND_FILE_DIR / 'telegram_general'
    module_command_dir.mkdir(parents=True, exist_ok=True)
    command__file_path = module_command_dir / command_file_name

    with open(command_file_path, "w", encoding="utf-8") as f:
        json.dump(command_data, f, ensure_ascii=False, indent=2)

    bot.reply_to(message, f"✅ Command received and saved as `{command_file_path}`.")
    log_local_bot_event(f"Saved command from {chat_id} to {command_file_path}")

if __name__ == '__main__':
    log_local_bot_event("Bot starting...")
    bot.polling()
    log_local_bot_event("Bot stopped.")
