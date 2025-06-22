import telebot
import json
import os
from pathlib import Path
from datetime import datetime
import logging # Added for better logging
import time # For sleep in polling loop

# Ensure nlp_services is discoverable
import sys
# Assuming katana_bot.py is in bot/ and nlp_services/ is at the project root (parent of bot/)
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from nlp_services.anthropic_client import get_anthropic_chat_response
from nlp_services.openai_client import get_openai_chat_response
from nlp_services.base_nlp_client import NLPServiceError # To catch all custom NLP errors

# Setup basic logging for the bot
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger.info("Initializing Katana Bot...")

# Получаем токен из переменной окружения
API_TOKEN = os.getenv('KATANA_TELEGRAM_TOKEN') # Removed default to rely on check

if not API_TOKEN:
    logger.critical("FATAL: KATANA_TELEGRAM_TOKEN environment variable not set.")
    raise ValueError("❌ KATANA_TELEGRAM_TOKEN environment variable not set. Bot cannot start.")
elif ':' not in API_TOKEN: # Basic format check
    logger.critical(f"FATAL: KATANA_TELEGRAM_TOKEN format is invalid. Token: {API_TOKEN[:3]}...{API_TOKEN[-3:] if len(API_TOKEN) > 6 else ''}")
    raise ValueError("❌ Invalid Telegram API token format. Expected format '123456:ABCDEF'.")
else:
    masked_token = f"{API_TOKEN.split(':')[0][:3]}...:{API_TOKEN.split(':')[-1][-3:]}" if ':' in API_TOKEN and len(API_TOKEN.split(':')[0]) > 3 and len(API_TOKEN.split(':')[-1]) > 3 else f"{API_TOKEN[:3]}...{API_TOKEN[-3:] if len(API_TOKEN) > 6 else ''}"
    logger.info(f"Telegram API Token loaded successfully (masked: {masked_token}).")

try:
    bot = telebot.TeleBot(API_TOKEN)
    logger.info("TeleBot instance created successfully.")
except Exception as e:
    logger.critical(f"FATAL: Failed to create TeleBot instance: {e}", exc_info=True)
    # Depending on desired behavior, could re-raise or sys.exit()
    raise # Re-raise to prevent running with a non-functional bot object

# Папка для сохранения команд
COMMAND_FILE_DIR = Path('commands')
COMMAND_FILE_DIR.mkdir(parents=True, exist_ok=True)

def log_local_bot_event(message, level=logging.INFO, **kwargs):
    """Логирование события бота с использованием стандартного модуля logging."""
    # Construct a base message string
    log_message = f"[BOT EVENT] {message}"

    # Use the appropriate logger method based on the level
    if level == logging.DEBUG:
        logger.debug(log_message, **kwargs)
    elif level == logging.INFO:
        logger.info(log_message, **kwargs)
    elif level == logging.WARNING:
        logger.warning(log_message, **kwargs)
    elif level == logging.ERROR:
        logger.error(log_message, **kwargs)
    elif level == logging.CRITICAL:
        logger.critical(log_message, **kwargs)
    else: # Default to INFO if level is unknown or not set
        logger.info(log_message, **kwargs)


def handle_log_event(command_data, chat_id):
    """Обработка команды 'log_event' (заглушка)."""
    log_local_bot_event(f"handle_log_event called for chat_id {chat_id} with data: {command_data}")

def handle_mind_clearing(command_data, chat_id):
    """Обработка команды 'mind_clearing' (заглушка)."""
    log_local_bot_event(f"handle_mind_clearing called for chat_id {chat_id} with data: {command_data}")

@bot.message_handler(commands=['start'])
def handle_start(message):
    """Ответ на /start"""
    bot.reply_to(message, "Привет! Я — Katana. Отправь JSON-команду, чтобы начать.")
    log_local_bot_event(f"/start received from {message.chat.id}")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Главный обработчик входящих сообщений."""
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else "N/A"
    command_text = message.text

    log_local_bot_event(f"Received message. ChatID: {chat_id}, UserID: {user_id}, Text: \"{command_text}\"")

    try: # Outermost try-except for the entire handler
        try:
            command_data = json.loads(command_text)
        except json.JSONDecodeError:
            bot.reply_to(message, "❌ Error: Invalid JSON format.")
            log_local_bot_event(f"Invalid JSON from {chat_id}: {command_text}")
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
                log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text})")
                return
            if field == "id":
                if not any(isinstance(command_data[field], t) for t in expected_type):
                    error_msg = f"❌ Error: Field '{field}' must be type str or int. Got {type(command_data[field]).__name__}."
                    bot.reply_to(message, error_msg)
                    log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text})")
                    return
            elif not isinstance(command_data[field], expected_type):
                error_msg = f"❌ Error: Field '{field}' must be type {expected_type.__name__}. Got {type(command_data[field]).__name__}."
                bot.reply_to(message, error_msg)
                log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text})")
                return

        command_type = command_data.get("type")

        if command_type == "log_event":
            handle_log_event(command_data, chat_id)
            bot.reply_to(message, "✅ 'log_event' processed (placeholder).")
            return
        elif command_type == "mind_clearing":
            handle_mind_clearing(command_data, chat_id)
            bot.reply_to(message, "✅ 'mind_clearing' processed (placeholder).")
            return

        # Check for NLP modules
        module_name = command_data.get("module")

        if module_name in ["anthropic_chat", "openai_chat"]:
            args = command_data.get("args", {})
            prompt = args.get("prompt")
            history = args.get("history", [])
            # For model_name, system_prompt, max_tokens, pass None if not provided, client functions have defaults
            model_name_arg = args.get("model_name") # client functions handle None
            system_prompt_arg = args.get("system_prompt") # client functions handle None
            max_tokens_arg = args.get("max_tokens") # client functions handle None

            if not prompt:
                bot.reply_to(message, f"❌ Error: 'prompt' is a required argument in 'args' for module '{module_name}'.")
                log_local_bot_event(f"Missing 'prompt' for {module_name} from {chat_id}", level=logging.ERROR)
                return

            try:
                log_local_bot_event(f"Processing '{module_name}' for {chat_id}. Prompt: '{prompt[:50]}...'")
                assistant_response = None
                if module_name == "anthropic_chat":
                    assistant_response = get_anthropic_chat_response(
                        history=history,
                        user_prompt=prompt,
                        model_name=model_name_arg if model_name_arg else "claude-3-opus-20240229", # Explicitly pass client default if None
                        system_prompt=system_prompt_arg,
                        max_tokens_to_sample=max_tokens_arg if max_tokens_arg is not None else 1024 # Pass client default if arg is None
                    )
                elif module_name == "openai_chat":
                    assistant_response = get_openai_chat_response(
                        history=history,
                        user_prompt=prompt,
                        model_name=model_name_arg if model_name_arg else "gpt-3.5-turbo", # Explicitly pass client default if None
                        system_prompt=system_prompt_arg,
                        max_tokens=max_tokens_arg if max_tokens_arg is not None else 1024 # Pass client default if arg is None
                    )

                bot.reply_to(message, f"🤖: {assistant_response}")
                log_local_bot_event(f"Successfully replied to '{module_name}' for {chat_id}. Response: '{str(assistant_response)[:50]}...'")

            except NLPServiceError as e:
                log_local_bot_event(
                    f"NLP Error for module {module_name} from {chat_id}: {str(e)}. User message: {e.user_message}",
                    level=logging.ERROR,
                    exc_info=True if e.original_error else False # Log stack trace if original error exists
                )
                bot.reply_to(message, f"🤖⚠️: {e.user_message}")
            except Exception as e:
                log_local_bot_event(
                    f"Unexpected error processing {module_name} for {chat_id}: {str(e)}",
                    level=logging.ERROR,
                    exc_info=True
                )
                bot.reply_to(message, "🤖⚠️: Произошла внутренняя ошибка при обработке вашего запроса.")
            return # NLP command processed or errored out

        # Fallback for other modules or if type was not log_event/mind_clearing
        log_local_bot_event(f"Command type '{command_type}' with module '{module_name}' not specifically handled by NLP, proceeding with default save.")

        # Ensure module_name for file saving uses the actual module name or a default
        effective_module_name = module_name if module_name else 'telegram_general'
        timestamp_str = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
        command_file_name = f"{timestamp_str}_{chat_id}.json"

        module_command_dir = COMMAND_FILE_DIR / f"telegram_mod_{effective_module_name}" if effective_module_name != 'telegram_general' else COMMAND_FILE_DIR / 'telegram_general'
        module_command_dir.mkdir(parents=True, exist_ok=True)
        command_file_path = module_command_dir / command_file_name

        with open(command_file_path, "w", encoding="utf-8") as f:
            json.dump(command_data, f, ensure_ascii=False, indent=2)

        bot.reply_to(message, f"✅ Command received and saved as `{command_file_path}`.")
        log_local_bot_event(f"Saved command from {chat_id} to {command_file_path}")

    except Exception as e: # Outermost catch-all for handle_message
        log_local_bot_event(
            f"Critical error in handle_message for chat {chat_id}, user {user_id}. Text: \"{command_text}\". Error: {str(e)}",
            level=logging.CRITICAL, # Use CRITICAL for unhandled errors in message handler
            exc_info=True
        )
        try:
            bot.reply_to(message, "🤖⚠️: Извините, произошла внутренняя ошибка. Попробуйте позже или свяжитесь с администратором.")
        except Exception as reply_e:
            logger.critical(f"Failed to send error reply to chat {chat_id}: {reply_e}", exc_info=True)


if __name__ == '__main__':
    # log_local_bot_event("Bot starting...") # Already logged by logger.info("Initializing Katana Bot...")
    logger.info("Attempting to start bot polling...")

    heartbeat_file_path = project_root / "katana_heartbeat.txt" # Heartbeat file in project root
    heartbeat_interval_seconds = 60 # How often to update heartbeat if we had an active loop
    last_heartbeat_time = 0

    while True:
        try:
            # Update heartbeat at the start of each polling attempt/iteration
            current_time = time.time()
            try:
                with open(heartbeat_file_path, "w") as f:
                    f.write(str(current_time))
                # Log less frequently for heartbeat, e.g., if it's part of a more active loop
                # For this setup, it logs on each polling restart/start.
                logger.info(f"Heartbeat updated at {heartbeat_file_path} with timestamp {current_time}")
            except IOError as ioe:
                logger.error(f"Failed to write heartbeat to {heartbeat_file_path}: {ioe}", exc_info=True)

            logger.info("Bot polling started with none_stop=True.")
            # In a real threaded scenario, the heartbeat write would be in a loop here too.
            # For now, it just means the polling *attempt* started.
            bot.polling(none_stop=True, interval=0) # interval=0 is default, can be omitted or tuned
        except Exception as e:
            logger.error(f"Bot polling encountered an error: {e}", exc_info=True)
            logger.info("Restarting polling in 15 seconds...")
            time.sleep(15)
        else: # This block executes if the try block completes without an exception (e.g., bot.stop_polling() was called)
            logger.info("Bot polling exited cleanly. Will restart if in a loop, or exit if stopped intentionally.")
            # If we want to truly stop on clean exit, we might break the while loop here.
            # For now, it will restart, which is robust for unexpected clean exits.
            # Consider adding a flag or condition to break loop if needed.
            time.sleep(5) # Brief pause before restarting even on clean exit, unless designed to stop.
    # log_local_bot_event("Bot stopped.") # This line would be unreachable if polling is in an infinite loop.