import telebot
import json
import os
from pathlib import Path
from datetime import datetime
import logging # Added for better logging
import time # For sleep in polling loop
import signal # For graceful shutdown

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

# --- Graceful Shutdown ---
shutdown_requested = False # Flag to indicate if shutdown was initiated by signal

def graceful_shutdown_handler(signum, frame):
    """Handles SIGINT and SIGTERM for graceful shutdown."""
    global shutdown_requested
    if not shutdown_requested: # Process signal only once
        shutdown_requested = True
        logger.warning(f"Shutdown signal {signal.Signals(signum).name} received. Attempting graceful shutdown...")
        if 'bot' in globals() and bot is not None:
            try:
                logger.info("Calling bot.stop_polling()...")
                bot.stop_polling()
                # Polling loop should exit after this.
            except Exception as e:
                logger.error(f"Error during bot.stop_polling(): {e}", exc_info=True)
        else:
            logger.warning("Bot object not available for stop_polling(). Exiting directly.")
        # Further cleanup can be added here if needed
    else:
        logger.warning(f"Repeated shutdown signal {signal.Signals(signum).name} received. Already shutting down.")

# Register signal handlers early, but bot object might not be ready if token fails
# We will register them in if __name__ == '__main__' after bot is created.

# --- End Graceful Shutdown ---

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

def run_bot_polling_loop(bot_instance, current_project_root, hb_file_path_obj, stop_flag_check_func):
    """
    Main polling loop for the bot, including heartbeat and restart logic.
    Args:
        bot_instance: The telebot.TeleBot instance.
        current_project_root: Path object for the project root. (Used for heartbeat path)
        hb_file_path_obj: Path object for the heartbeat file.
        stop_flag_check_func: A function that returns True if shutdown is requested.
    """
    logger.info("Bot polling loop initiated.")

    # heartbeat_interval_seconds = 60 # Defined but not used for an active inner loop
    # last_heartbeat_time = 0 # Defined but not used for an active inner loop

    while not stop_flag_check_func():
        try:
            current_timestamp = time.time() # Renamed from current_time to avoid conflict
            try:
                with open(hb_file_path_obj, "w") as f:
                    f.write(str(current_timestamp))
                logger.info(f"Heartbeat updated at {hb_file_path_obj} with timestamp {current_timestamp}")
            except IOError as ioe:
                logger.error(f"Failed to write heartbeat to {hb_file_path_obj}: {ioe}", exc_info=True)

            logger.info("Bot polling started with none_stop=True.")
            bot_instance.polling(none_stop=True, interval=0)

        except Exception as e:
            if stop_flag_check_func():
                logger.error(f"Bot polling error during shutdown: {e}", exc_info=True)
                break
            logger.error(f"Bot polling encountered an error: {e}", exc_info=True)
            logger.info("Restarting polling in 15 seconds...")

            for _ in range(15):
                if stop_flag_check_func():
                    logger.info("Shutdown requested during polling error sleep. Aborting restart.")
                    break
                time.sleep(1)
            if stop_flag_check_func(): break

        else:
            if stop_flag_check_func():
                logger.info("Bot polling exited cleanly due to shutdown request.")
                break
            else:
                logger.warning("Bot polling exited cleanly but no shutdown signal was received. Restarting in 5 seconds...")
                for _ in range(5):
                    if stop_flag_check_func():
                         logger.info("Shutdown requested during clean exit sleep. Aborting restart.")
                         break
                    time.sleep(1)
                if stop_flag_check_func(): break

    logger.info("Bot polling loop terminated.")


if __name__ == '__main__':
    logger.info("Attempting to start Katana Bot...") # Changed log message slightly

    signal.signal(signal.SIGINT, graceful_shutdown_handler)
    signal.signal(signal.SIGTERM, graceful_shutdown_handler)
    logger.info("Signal handlers for SIGINT and SIGTERM registered.")

    heartbeat_file = project_root / "katana_heartbeat.txt" # Use module-level project_root

    # The 'bot' global is used by graceful_shutdown_handler and now passed to run_bot_polling_loop
    run_bot_polling_loop(bot, project_root, heartbeat_file, lambda: shutdown_requested)

    logger.info("Katana Bot has shut down.")