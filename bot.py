import telebot
import json
import os
import logging # Added
import time
import requests
import threading
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock
from katana_state import KatanaState
from app.utils.log import log_command

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

bot = None

# Directory for storing command files
COMMAND_FILE_DIR = Path('commands')
COMMAND_FILE_DIR.mkdir(parents=True, exist_ok=True)

# Katana State Initialisation
katana_state = KatanaState()

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

def handle_n8n_trigger(command_data, chat_id):
    """Handles 'n8n_trigger' commands by sending a POST request to n8n."""
    n8n_webhook_url = "http://localhost:5678/webhook/Katana%20Orchestrator"
    katana_logger.info(f"Triggering n8n webhook for command: {command_data.get('katana_uid')}")

    retries = 3
    for i in range(retries):
        try:
            response = requests.post(n8n_webhook_url, json=command_data, timeout=10)
            response.raise_for_status()  # Raise an exception for bad status codes
            katana_logger.info(f"n8n webhook triggered successfully for {command_data.get('katana_uid')}. Response: {response.text}")
            # TODO: Send response back to the user/queue
            return
        except requests.exceptions.RequestException as e:
            katana_logger.warning(f"Attempt {i+1} failed to trigger n8n webhook for {command_data.get('katana_uid')}. Reason: {e}")
            if i < retries - 1:
                time.sleep(2 ** i)  # Exponential backoff
            else:
                katana_logger.error(f"Failed to trigger n8n webhook for {command_data.get('katana_uid')} after {retries} retries.")

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


def command_processor_loop():
    """
    The main loop for processing commands from the queue.
    Runs in a separate thread.
    """
    while True:
        command_data = katana_state.dequeue()
        if command_data is None:
            break
        try:
            katana_logger.info(f"Processing command: {command_data}")
            command_type = command_data.get("type")
            chat_id = command_data.get("chat_id", "N/A") # Assuming chat_id is passed in command_data
            katana_uid = command_data.get("katana_uid")
            log_command(
                command_id=katana_uid,
                command=command_type,
                args=command_data.get("args"),
                status="processing",
            )

            if command_type == "log_event":
                handle_log_event(command_data, chat_id)
                katana_logger.info(f"Successfully processed command: {command_type}")
                log_command(
                    command_id=katana_uid,
                    command=command_type,
                    args=command_data.get("args"),
                    status="success",
                )
            elif command_type == "mind_clearing":
                handle_mind_clearing(command_data, chat_id)
                katana_logger.info(f"Successfully processed command: {command_type}")
                log_command(
                    command_id=katana_uid,
                    command=command_type,
                    args=command_data.get("args"),
                    status="success",
                )
            elif command_type == "n8n_trigger":
                handle_n8n_trigger(command_data, chat_id)
                log_command(
                    command_id=katana_uid,
                    command=command_type,
                    args=command_data.get("args"),
                    status="success",
                )
            else:
                katana_logger.warning(f"Unknown command type: {command_type}")
                log_command(
                    command_id=katana_uid,
                    command=command_type,
                    args=command_data.get("args"),
                    status="failed",
                    error="Unknown command type",
                )
        except Exception as e:
            katana_logger.error(f"Error processing command: {command_data}. Reason: {e}", exc_info=True)
            log_command(
                command_id=katana_uid,
                command=command_type,
                args=command_data.get("args"),
                status="failed",
                error=str(e),
            )
        finally:
            katana_state.task_done()
            if "callback_url" in command_data:
                try:
                    requests.post(command_data["callback_url"], json=command_data)
                except requests.exceptions.RequestException as e:
                    katana_logger.error(f"Failed to send callback for {katana_uid}. Reason: {e}")

def handle_message_logic(bot, message):
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

    # 3. Enqueue Command
    command_data['chat_id'] = chat_id
    katana_uid = katana_state.enqueue(command_data)
    log_command(
        command_id=katana_uid,
        command=command_data.get("type"),
        args=command_data.get("args"),
        status="queued",
    )
    bot.reply_to(message, f"✅ Command received and queued with ID: {katana_uid}")
    katana_logger.info(f"Enqueued command from {chat_id} with Katana UID: {katana_uid}")

def register_handlers(bot):
    @bot.message_handler(func=lambda message: True)
    def handle_message(message):
        handle_message_logic(bot, message)

def create_bot(token, bot_class=telebot.TeleBot):
    bot = bot_class(token)
    register_handlers(bot)
    return bot

def main():
    bot = create_bot(API_TOKEN)
    katana_logger.info("Bot starting...")
    # Start the command processor in a background thread
    processor_thread = threading.Thread(target=command_processor_loop, daemon=True)
    processor_thread.start()
    katana_logger.info("Command processor thread started.")

    try:
        bot.polling()
    except Exception as e:
        katana_logger.error(f"Bot polling failed: {e}", exc_info=True) # Log exception info
    finally:
        katana_logger.info("Bot stopped.")

if __name__ == '__main__':
    main()
