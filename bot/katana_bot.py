import telebot
import json
import os
import logging
from pathlib import Path
from datetime import datetime

from bot.nlp_clients.anthropic_client import AnthropicClient, AnthropicClientError
from bot.nlp_clients.openai_client import OpenAIClient, OpenAIClientError
from bot.nlp_clients.base_nlp_client import NLPServiceError

import logging.handlers # For RotatingFileHandler
import threading
import time

# --- Logging Setup ---
LOG_DIR = Path(__file__).parent.parent / 'logs' # Assuming logs directory at project root
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE_PATH = LOG_DIR / 'katana_bot.log'
HEARTBEAT_FILE_PATH = LOG_DIR / 'heartbeat.txt'
HEARTBEAT_INTERVAL = 60 # seconds

logger = logging.getLogger(__name__) # Get the logger for this module
logger.setLevel(logging.INFO) # Set the default level for this logger

# Formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Stream Handler (console)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

# Rotating File Handler
# Rotate logs at 5MB, keep 5 backup files
rotating_file_handler = logging.handlers.RotatingFileHandler(
    LOG_FILE_PATH, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8'
)
rotating_file_handler.setFormatter(formatter)
logger.addHandler(rotating_file_handler)

# Remove basicConfig as we are configuring handlers manually for the specific logger.
# logging.basicConfig(...) would configure the root logger.

# --- Environment Variables & Bot Initialization ---
API_TOKEN = os.getenv('KATANA_TELEGRAM_TOKEN')
if API_TOKEN and ':' in API_TOKEN:
    logger.info("✅ Telegram API token loaded successfully.")
else:
    logger.error("❌ Invalid or missing Telegram API token. Please set KATANA_TELEGRAM_TOKEN env variable with format '123456:ABCDEF'.")
    raise ValueError("❌ Invalid or missing Telegram API token. Please set KATANA_TELEGRAM_TOKEN env variable with format '123456:ABCDEF'.")

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', "dummy_anthropic_key_env")
if ANTHROPIC_API_KEY == "dummy_anthropic_key_env":
    logger.warning("⚠️ Anthropic API key is using the default dummy value. Set ANTHROPIC_API_KEY for actual use.")
else:
    logger.info("✅ Anthropic API key loaded.")

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', "dummy_openai_key_env")
if OPENAI_API_KEY == "dummy_openai_key_env":
    logger.warning("⚠️ OpenAI API key is using the default dummy value. Set OPENAI_API_KEY for actual use.")
else:
    logger.info("✅ OpenAI API key loaded.")


bot = telebot.TeleBot(API_TOKEN)

# --- Constants ---
COMMAND_FILE_DIR = Path('commands')
COMMAND_FILE_DIR.mkdir(parents=True, exist_ok=True)

NLP_MODULE_ANTHROPIC = "anthropic_chat"
NLP_MODULE_OPENAI = "openai_chat"

# --- Utility Functions (Replaces log_local_bot_event) ---
# No longer needed, using standard logger

# --- Placeholder Handlers ---
def handle_log_event(command_data, chat_id):
    """Обработка команды 'log_event' (заглушка)."""
    logger.info(f"handle_log_event called for chat_id {chat_id} with data: {command_data}")

def handle_mind_clearing(command_data, chat_id):
    """Обработка команды 'mind_clearing' (заглушка)."""
    logger.info(f"handle_mind_clearing called for chat_id {chat_id} with data: {command_data}")

# --- NLP Core Logic ---
def get_nlp_response(user_prompt: str, module: str) -> str:
    """
    Gets a response from the specified NLP client.

    Args:
        user_prompt: The prompt to send to the NLP model.
        module: The NLP module to use (e.g., "anthropic_chat", "openai_chat").

    Returns:
        The NLP model's response string, or a user-friendly error message.
    """
    logger.info(f"Attempting to get NLP response for module: {module}")
    try:
        # Select and initialize the appropriate NLP client based on the module.
        if module == NLP_MODULE_ANTHROPIC:
            logger.info(f"Using Anthropic client. Prompt: '{user_prompt[:50]}...'")
            # Note: Client instantiation could be optimized in a production app (e.g., singleton pattern).
            client = AnthropicClient(api_key=ANTHROPIC_API_KEY)
            # The 'scenario' parameter is for the current mock client's behavior.
            # In a real integration, this would be a direct call to the actual client method.
            response = client.generate_text(prompt=user_prompt, scenario="success")
            logger.info(f"Anthropic client success. Response: '{response[:50]}...'")
            return response
        elif module == NLP_MODULE_OPENAI:
            logger.info(f"Using OpenAI client. Prompt: '{user_prompt[:50]}...'")
            client = OpenAIClient(api_key=OPENAI_API_KEY)
            response = client.generate_text(prompt=user_prompt, scenario="success")
            logger.info(f"OpenAI client success. Response: '{response[:50]}...'")
            return response
        else:
            # Handle cases where the module is not a known/supported NLP service.
            logger.warning(f"Unknown NLP module specified: {module}")
            return f"❌ Error: Unknown NLP module '{module}'. Cannot process request."

    except NLPServiceError as e:
        # Catch custom NLP exceptions from the clients.
        # These exceptions already have a user-friendly `user_message`.
        logger.error(
            f"NLPServiceError caught for module {module}. User Message: '{e.user_message}'. Original Error: {type(e.original_error).__name__} - {e.original_error}",
            exc_info=True # Adds stack trace to the log for detailed debugging.
        )
        return e.user_message # Return the user-friendly message to the end-user.
    except Exception as e:
        # Catch any other unexpected exceptions during NLP processing.
        logger.critical(
            f"Unexpected critical error during NLP processing for module {module}! Error: {type(e).__name__} - {e}",
            exc_info=True # Adds stack trace to the log.
        )
        # Return a generic error message to the user for unforeseen issues.
        return "❌ An unexpected system error occurred while trying to process your request. Please try again later."


# --- Telegram Bot Handlers ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    """Ответ на /start"""
    bot.reply_to(message, "Привет! Я — Katana. Отправь JSON-команду, чтобы начать.")
    logger.info(f"/start received from {message.chat.id}")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Главный обработчик входящих сообщений."""
    chat_id = message.chat.id
    command_text = message.text

    logger.info(f"Received message from {chat_id}: {command_text}")

    try: # Top-level try-except for the entire message handling logic
        try:
            command_data = json.loads(command_text)
        except json.JSONDecodeError:
            reply_text = "❌ Error: Invalid JSON format."
        bot.reply_to(message, reply_text)
        logger.warning(f"Invalid JSON from {chat_id}: {command_text}. Replied: '{reply_text}'", exc_info=True)
        return

    required_fields = {
        "type": str,
        "module": str,
        "args": dict,
        "id": (str, int)
    }

    for field, expected_type in required_fields.items():
        if field not in command_data:
            error_msg = f"❌ Error: Missing required field '{field}'."
            bot.reply_to(message, error_msg)
            logger.warning(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text})")
            return
        if field == "id":
            if not any(isinstance(command_data[field], t) for t in expected_type): # type: ignore
                error_msg = f"❌ Error: Field '{field}' must be type str or int. Got {type(command_data[field]).__name__}."
                bot.reply_to(message, error_msg)
                logger.warning(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text})")
                return
        elif not isinstance(command_data[field], expected_type): # type: ignore
            error_msg = f"❌ Error: Field '{field}' must be type {expected_type.__name__}. Got {type(command_data[field]).__name__}." # type: ignore
            bot.reply_to(message, error_msg)
            logger.warning(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text})")
            return

    command_type = command_data.get("type")
    module_name = command_data.get("module")
    command_type = command_data.get("type") # Already got this, but make sure it's used for routing NLP

    # --- NLP Module Handling ---
    # Check if the command type indicates an NLP operation.
    # If so, delegate to `get_nlp_response` which handles specific module validation and client calls.
    if command_type == "nlp_query": # "nlp_query" is the designated type for NLP actions.
        if not module_name: # Module name is essential for routing to the correct NLP client.
            reply_text = "❌ Error: Missing 'module' field for NLP command."
            bot.reply_to(message, reply_text)
            logger.warning(f"NLP command validation failed for {chat_id}: {reply_text} (Command: {command_text})")
            return

        user_prompt = command_data.get("args", {}).get("prompt")
        if not user_prompt or not isinstance(user_prompt, str):
            reply_text = "❌ Error: Missing 'prompt' in 'args' for NLP command or it's not a string."
            bot.reply_to(message, reply_text)
            logger.warning(f"NLP command validation failed for {chat_id}: {reply_text} (Command: {command_text})")
            return

        nlp_response = get_nlp_response(user_prompt, module_name)
        bot.reply_to(message, nlp_response)
        # Log based on whether nlp_response indicates an error (starts with ❌) or success
        if nlp_response.startswith("❌"):
            logger.warning(f"Sent NLP error reply to {chat_id} for module {module_name}. Reply: '{nlp_response}'")
        else:
            logger.info(f"Sent NLP success reply to {chat_id} for module {module_name}. Reply: '{nlp_response[:100]}...'")
        return

    # --- Existing Command Type Handling (Non-NLP) ---
    if command_type == "log_event":
        handle_log_event(command_data, chat_id)
        reply_text = "✅ 'log_event' processed (placeholder)."
        bot.reply_to(message, reply_text)
        logger.info(f"Sent '{command_type}' confirmation to {chat_id}. Reply: '{reply_text}'")
        return
    elif command_type == "mind_clearing":
        handle_mind_clearing(command_data, chat_id)
        reply_text = "✅ 'mind_clearing' processed (placeholder)."
        bot.reply_to(message, reply_text)
        logger.info(f"Sent '{command_type}' confirmation to {chat_id}. Reply: '{reply_text}'")
        return

    # --- Default: Save command to file (if not an NLP module and not other specific types) ---
    logger.info(f"Command type '{command_type}' for module '{module_name}' not specifically handled by NLP or other handlers, proceeding with default save.")

    timestamp_str = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
    command_file_name = f"{timestamp_str}_{chat_id}.json"

    # Ensure module_name for directory is not None, default to 'telegram_general' if it was
    dir_module_name = module_name if module_name else 'telegram_general'
    module_command_dir = COMMAND_FILE_DIR / f"telegram_mod_{dir_module_name}"
    module_command_dir.mkdir(parents=True, exist_ok=True)
    command_file_path = module_command_dir / command_file_name

    try:
        with open(command_file_path, "w", encoding="utf-8") as f:
            json.dump(command_data, f, ensure_ascii=False, indent=2)
        reply_text = f"✅ Command received and saved as `{command_file_path}`."
        bot.reply_to(message, reply_text)
        logger.info(f"Saved command from {chat_id} to {command_file_path}. Replied: '{reply_text}'")
    except Exception as e:
        logger.error(f"Error saving command file for {chat_id} to {command_file_path}: {e}", exc_info=True)
        reply_text = "❌ Error: Could not save your command due to a server-side issue."
        bot.reply_to(message, reply_text)
        logger.error(f"Sent file save error reply to {chat_id}. Reply: '{reply_text}'")

    except Exception as e:
        # Catch-all for any other unhandled exception during message processing
        logger.critical(
            f"Unhandled exception in handle_message for chat_id {chat_id}. Command: '{command_text}'. Error: {e}",
            exc_info=True
        )
        reply_text = "🤖 Ой, что-то пошло не так на моей стороне. Я уже разбираюсь. Попробуйте свой запрос чуть позже."
        try:
            bot.reply_to(message, reply_text)
            logger.info(f"Sent generic error reply to {chat_id} due to unhandled exception. Reply: '{reply_text}'")
        except Exception as reply_e:
            # If even replying fails, log that too.
            logger.error(f"Failed to send generic error reply to {chat_id}. Error during reply: {reply_e}", exc_info=True)

# --- Heartbeat Function ---
def _update_heartbeat():
    """Periodically updates the heartbeat file with the current timestamp."""
    while True:
        try:
            with open(HEARTBEAT_FILE_PATH, "w", encoding="utf-8") as f:
                f.write(datetime.utcnow().isoformat())
            # logger.debug(f"Heartbeat updated at {HEARTBEAT_FILE_PATH}") # Optional: log successful heartbeat
        except Exception as e:
            logger.error(f"Failed to update heartbeat file: {e}", exc_info=True)
        time.sleep(HEARTBEAT_INTERVAL)

def main():
    """Starts the KatanaBot."""
    logger.info("🚀 KatanaBot starting up...")

    # Start heartbeat thread
    heartbeat_thread = threading.Thread(target=_update_heartbeat, daemon=True)
    # Daemon threads exit when the main program exits
    heartbeat_thread.start()
    logger.info(f"❤️ Heartbeat thread started. Updates every {HEARTBEAT_INTERVAL}s to '{HEARTBEAT_FILE_PATH}'.")

    logger.info("Polling mode: continuous (none_stop=True)")
    try:
        # none_stop=True ensures the bot keeps running even after some errors,
        # attempting to reconnect and continue polling.
        bot.polling(none_stop=True)
    except Exception as e:
        # This will typically catch errors if none_stop=False, or critical setup/library errors.
        # With none_stop=True, most operational errors are handled internally by telebot or should be caught in handlers.
        logger.critical(f"Bot polling loop exited critically: {e}", exc_info=True)
    finally:
        logger.info("Bot stopped.")

if __name__ == '__main__':
    main()