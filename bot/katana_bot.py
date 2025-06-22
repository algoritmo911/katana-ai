import telebot
import json
import os
import logging
from pathlib import Path
from datetime import datetime

from bot.nlp_clients.anthropic_client import AnthropicClient, AnthropicClientError
from bot.nlp_clients.openai_client import OpenAIClient, OpenAIClientError
from bot.nlp_clients.base_nlp_client import NLPServiceError

# --- Logging Setup ---
# Remove basicConfig if a more sophisticated setup is added later (e.g. from a config file)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()] # Output to console
)
logger = logging.getLogger(__name__)

# --- Environment Variables & Bot Initialization ---
API_TOKEN = os.getenv('KATANA_TELEGRAM_TOKEN')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', "dummy_anthropic_key_env") # Provide a default for local dev if not set
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', "dummy_openai_key_env") # Provide a default for local dev if not set

if not API_TOKEN or ':' not in API_TOKEN:
    logger.error("❌ Invalid or missing Telegram API token. Please set KATANA_TELEGRAM_TOKEN env variable.")
    raise ValueError("❌ Invalid or missing Telegram API token. Please set KATANA_TELEGRAM_TOKEN env variable with format '123456:ABCDEF'.")

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

    try:
        command_data = json.loads(command_text)
    except json.JSONDecodeError:
        bot.reply_to(message, "❌ Error: Invalid JSON format.")
        logger.warning(f"Invalid JSON from {chat_id}: {command_text}", exc_info=True)
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
            error_msg = "❌ Error: Missing 'module' field for NLP command."
            bot.reply_to(message, error_msg)
            logger.warning(f"NLP command validation failed for {chat_id}: {error_msg} (Command: {command_text})")
            return

        user_prompt = command_data.get("args", {}).get("prompt")
        if not user_prompt or not isinstance(user_prompt, str):
            error_msg = "❌ Error: Missing 'prompt' in 'args' for NLP command or it's not a string."
            bot.reply_to(message, error_msg)
            logger.warning(f"NLP command validation failed for {chat_id}: {error_msg} (Command: {command_text})")
            return

        nlp_response = get_nlp_response(user_prompt, module_name)
        bot.reply_to(message, nlp_response)
        logger.info(f"Sent NLP response to {chat_id} for module {module_name}.")
        return

    # --- Existing Command Type Handling (Non-NLP) ---
    if command_type == "log_event":
        handle_log_event(command_data, chat_id)
        bot.reply_to(message, "✅ 'log_event' processed (placeholder).")
        return
    elif command_type == "mind_clearing":
        handle_mind_clearing(command_data, chat_id)
        bot.reply_to(message, "✅ 'mind_clearing' processed (placeholder).")
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
        bot.reply_to(message, f"✅ Command received and saved as `{command_file_path}`.")
        logger.info(f"Saved command from {chat_id} to {command_file_path}")
    except Exception as e:
        logger.error(f"Error saving command file for {chat_id} to {command_file_path}: {e}", exc_info=True)
        bot.reply_to(message, "❌ Error: Could not save your command due to a server-side issue.")


if __name__ == '__main__':
    logger.info("Bot starting...")
    try:
        bot.polling()
    except Exception as e:
        logger.critical(f"Bot polling failed critically: {e}", exc_info=True)
    finally:
        logger.info("Bot stopped.")