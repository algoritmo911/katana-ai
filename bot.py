import telebot
import json
import os
import logging # Added
from pathlib import Path
from datetime import datetime

# --- Logger Setup ---
katana_logger = logging.getLogger('katana_logger')
katana_logger.setLevel(logging.INFO)

# File Handler
file_handler = logging.FileHandler('katana_bot.log')
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
katana_logger.addHandler(file_handler)

# Console Handler
console_handler = logging.StreamHandler()
console_formatter = logging.Formatter('[%(levelname)s] %(message)s')
console_handler.setFormatter(console_formatter)
katana_logger.addHandler(console_handler)
# --- End Logger Setup ---

# TODO: Get API token from environment variable or secrets manager
API_TOKEN = 'YOUR_API_TOKEN'

bot = telebot.TeleBot(API_TOKEN)

# Directory for storing command files
COMMAND_FILE_DIR = Path('commands')
COMMAND_FILE_DIR.mkdir(parents=True, exist_ok=True)

# Removed log_local_bot_event function

def handle_log_event(command_data, chat_id):
    """Handles 'log_event' commands by logging their arguments."""
    # Ensure 'module' and 'args' are present, though validation should have caught this.
    # Adding default values or checks here for robustness in the handler itself can be good practice.
    module_name = command_data.get('module', 'UnknownModule')
    event_args = command_data.get('args', {})

    katana_logger.info(f"EVENT LOGGED by {chat_id} for module {module_name}: {event_args}")
    # Actual implementation for log_event (e.g., writing to a specific event store) could go here.
    # For now, logging the event details is the primary action.

def handle_mind_clearing(command_data, chat_id):
    """Placeholder for handling 'mind_clearing' commands."""
    katana_logger.info(f"handle_mind_clearing called for chat_id {chat_id} with data: {command_data}")
    # Actual implementation for mind_clearing will go here
    # bot.reply_to(message, "✅ 'mind_clearing' received (placeholder).") # TODO: Add reply mechanism

# --- Helper Functions for handle_message ---

def _parse_command(message_text, chat_id, logger):
    """
    Parses the incoming message text as JSON.
    Returns command_data dictionary on success, None on failure.
    Logs errors if parsing fails.
    """
    try:
        command_data = json.loads(message_text)
        return command_data
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON from {chat_id}: {message_text}")
        return None

def _validate_command(command_data, chat_id, required_fields, logger, command_text_for_logging):
    """
    Validates the parsed command data against required_fields.
    Returns (True, None) on success.
    Returns (False, error_message_for_user) on failure.
    Logs errors if validation fails.
    """
    for field, expected_types_tuple in required_fields.items():
        if field not in command_data:
            error_msg = f"Error: Missing required field '{field}'."
            logger.error(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text_for_logging})")
            return False, error_msg

        if not any(isinstance(command_data[field], t) for t in expected_types_tuple):
            expected_type_names = ' or '.join(t.__name__ for t in expected_types_tuple)
            error_msg = f"Error: Field '{field}' must be type {expected_type_names}. Got {type(command_data[field]).__name__}."
            logger.error(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text_for_logging})")
            return False, error_msg
    return True, None

# --- Main Message Handler ---

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Handles incoming messages."""
    chat_id = message.chat.id
    command_text = message.text

    katana_logger.info(f"Received message from {chat_id}: {command_text}")

    # 1. Parse Command
    command_data = _parse_command(command_text, chat_id, katana_logger)
    if command_data is None:
        bot.reply_to(message, "Error: Invalid JSON format.")
        # _parse_command already logs the detailed error
        return

    # 2. Validate Command
    # Definition of required fields for command structure
    required_fields = {
        "type": (str,),
        "module": (str,),
        "args": (dict,),
        "id": (str, int)  # id can be string or integer
    }
    is_valid, validation_error_msg = _validate_command(command_data, chat_id, required_fields, katana_logger, command_text)
    if not is_valid:
        bot.reply_to(message, validation_error_msg)
        # _validate_command already logs the detailed error
        return

    # 3. Command routing based on 'type' (if parsing and validation are successful)
    command_type = command_data.get("type")

    if command_type == "log_event":
        handle_log_event(command_data, chat_id)
        bot.reply_to(message, "✅ 'log_event' processed (placeholder).")
        katana_logger.info(f"Successfully processed command for {chat_id}: {command_type}")
        return
    elif command_type == "mind_clearing":
        handle_mind_clearing(command_data, chat_id)
        bot.reply_to(message, "✅ 'mind_clearing' processed (placeholder).")
        katana_logger.info(f"Successfully processed command for {chat_id}: {command_type}")
        return

    # If type is not matched, proceed with default behavior (saving)
    katana_logger.info(f"Command type '{command_type}' for chat_id {chat_id} not specifically handled, proceeding with default save.")

    # Save the command to a file
    timestamp_str = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
    command_file_name = f"{timestamp_str}_{chat_id}.json"

    module_name = command_data.get('module', 'telegram_general') # Module name validated to exist by this point
    module_command_dir = COMMAND_FILE_DIR / f"telegram_mod_{module_name}" if module_name != 'telegram_general' else COMMAND_FILE_DIR / 'telegram_general'
    module_command_dir.mkdir(parents=True, exist_ok=True)
    command_file_path = module_command_dir / command_file_name

    try:
        with open(command_file_path, "w", encoding="utf-8") as f:
            json.dump(command_data, f, ensure_ascii=False, indent=2)
        bot.reply_to(message, f"✅ Command received and saved as `{command_file_path}`.")
        katana_logger.info(f"Saved command from {chat_id} to {command_file_path}")
    except IOError as e:
        katana_logger.error(f"Failed to save command for {chat_id} to {command_file_path}. Reason: {e}")
        bot.reply_to(message, f"Error: Could not save command. Please contact administrator.")
        # Optionally, add more specific error handling or re-raise

if __name__ == '__main__':
    katana_logger.info("Bot starting...")
    try:
        bot.polling()
    except Exception as e:
        katana_logger.error(f"Bot polling failed: {e}", exc_info=True) # Log exception info
    finally:
        katana_logger.info("Bot stopped.")
