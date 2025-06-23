import telebot
import json
import os
from pathlib import Path
from datetime import datetime
import subprocess # Added for run_katana_command
from nlp_mapper import interpret # Added for NLP

# TODO: Get API token from environment variable or secrets manager
# Using a format-valid dummy token for testing purposes if no env var is set.
API_TOKEN = os.environ.get('TELEGRAM_API_TOKEN', '12345:dummytoken')

bot = telebot.TeleBot(API_TOKEN)

# Directory for storing command files
COMMAND_FILE_DIR = Path('commands')
COMMAND_FILE_DIR.mkdir(parents=True, exist_ok=True)

# --- Logging Setup ---
LOG_DIR = Path('logs') # Changed to relative path
LOG_DIR.mkdir(parents=True, exist_ok=True)
TELEGRAM_BOT_LOG_FILE = LOG_DIR / 'telegram_bot.log' # Changed filename from task

def log_telegram_message(message_data: str):
    """Appends a structured message to the telegram_bot.log file."""
    with open(TELEGRAM_BOT_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.utcnow().isoformat()} | {message_data}\n")

def log_local_bot_event(message: str): # Renamed for clarity, though it's used internally
    """Logs an internal bot event to the console and to the telegram_bot.log file."""
    log_entry = f"[BOT_INTERNAL_EVENT] {message}"
    print(f"{datetime.utcnow().isoformat()} | {log_entry}")
    log_telegram_message(log_entry)


# --- Katana Command Execution ---
def run_katana_command(command: str) -> str:
    """
    Executes a shell command and returns its output.
    This is a simplified placeholder. In a real scenario, this would interact
    with a more complex 'katana_agent' or similar.
    """
    log_local_bot_event(f"Running katana command: {command}")
    try:
        # Using shell=True for simplicity with complex commands like pipes.
        # Be cautious with shell=True in production due to security risks.
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True, timeout=30)
        output = result.stdout.strip()
        if result.stderr.strip():
            output += f"\nStderr:\n{result.stderr.strip()}"
        log_local_bot_event(f"Command output: {output}")
        return output
    except subprocess.CalledProcessError as e:
        error_message = f"Error executing command '{command}': {e.stderr.strip()}"
        log_local_bot_event(error_message)
        return error_message
    except subprocess.TimeoutExpired:
        error_message = f"Command '{command}' timed out."
        log_local_bot_event(error_message)
        return error_message
    except Exception as e:
        error_message = f"An unexpected error occurred while running command '{command}': {str(e)}"
        log_local_bot_event(error_message)
        return error_message

def handle_log_event(command_data, chat_id):
    """Placeholder for handling 'log_event' commands."""
    log_local_bot_event(f"handle_log_event called for chat_id {chat_id} with data: {json.dumps(command_data)}")
    # Actual implementation for log_event will go here
    # TODO: Add more specific logging based on args if needed
    log_local_bot_event(f"Successfully processed 'log_event' for chat_id {chat_id}. Args: {json.dumps(command_data.get('args'))}")
    # bot.reply_to(message, "✅ 'log_event' received (placeholder).") # TODO: Add reply mechanism

def handle_mind_clearing(command_data, chat_id):
    """Placeholder for handling 'mind_clearing' commands."""
    log_local_bot_event(f"handle_mind_clearing called for chat_id {chat_id} with data: {json.dumps(command_data)}")
    # Actual implementation for mind_clearing will go here
    # TODO: Add more specific logging based on args if needed
    log_local_bot_event(f"Successfully processed 'mind_clearing' for chat_id {chat_id}. Args: {json.dumps(command_data.get('args'))}")
    # bot.reply_to(message, "✅ 'mind_clearing' received (placeholder).") # TODO: Add reply mechanism

# --- Standard Command Handlers ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Handles the /start command."""
    chat_id = message.chat.id
    user_name = message.from_user.first_name
    reply_text = f"Привет, {user_name}! Я Katana, твой Telegram-помощник. Готов к работе!"
    log_telegram_message(f"Incoming: {message.text} from {chat_id}. Outgoing: {reply_text}")
    bot.reply_to(message, reply_text)

@bot.message_handler(commands=['help'])
def send_help(message):
    """Handles the /help command."""
    chat_id = message.chat.id
    reply_text = (
        "Доступные команды:\n"
        "/start - Начало работы\n"
        "/help - Эта справка\n"
        "/status - Текущий статус бота\n"
        "/stop - Остановить бота\n\n"
        "Также я понимаю некоторые ключевые слова, например, 'привет', 'помощь', 'стоп'."
    )
    log_telegram_message(f"Incoming: {message.text} from {chat_id}. Outgoing: {reply_text}")
    bot.reply_to(message, reply_text)

@bot.message_handler(commands=['status'])
def send_status(message):
    """Handles the /status command."""
    chat_id = message.chat.id
    reply_text = "Бот жив и работает!"
    log_telegram_message(f"Incoming: {message.text} from {chat_id}. Outgoing: {reply_text}")
    bot.reply_to(message, reply_text)

@bot.message_handler(commands=['stop'])
def stop_bot_handler(message):
    """Handles the /stop command."""
    chat_id = message.chat.id
    reply_text = "Останавливаю работу... До встречи!"
    log_telegram_message(f"Incoming: {message.text} from {chat_id}. Outgoing: {reply_text}")
    bot.reply_to(message, reply_text)
    log_local_bot_event("Stopping polling as per /stop command.")
    bot.stop_polling()


# This will be the new text handler
@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text_message(message):
    """Handles incoming text messages, keywords, NLP, and JSON commands."""
    chat_id = message.chat.id
    text = message.text
    text_lower = text.lower()

    log_telegram_message(f"Incoming text message from {chat_id}: {text}")

    # Keyword handling
    if "привет" in text_lower:
        reply_text = "Привет! Чем могу помочь?"
        log_telegram_message(f"Keyword 'привет' detected. Outgoing: {reply_text}")
        bot.reply_to(message, reply_text)
        return
    elif "помощь" in text_lower: # Reacting to "помощь" keyword
        send_help(message) # Reuse the /help handler logic
        return
    elif "стоп" in text_lower and chat_id == message.from_user.id: # Check if it's a private message or use admin check
        # Added a basic check to prevent group "stop" triggers, can be more sophisticated
        reply_text = "Понял, останавливаюсь по ключевому слову 'стоп'."
        log_telegram_message(f"Keyword 'стоп' detected. Outgoing: {reply_text}")
        bot.reply_to(message, reply_text)
        log_local_bot_event("Stopping polling due to 'стоп' keyword.")
        bot.stop_polling()
        return

    # Attempt to interpret the text as a natural language command (NLP)
    # Check if the text is not a command before attempting NLP or JSON parsing.
    # This prevents trying to NLP/JSON parse /start, /help etc.
    if not text.startswith('/'):
        nlp_command = interpret(text)
        if nlp_command:
            log_telegram_message(f'[NLU] "{text}" → "{nlp_command}"')
            output = run_katana_command(nlp_command)
            reply_text = f"🧠 Понял. Выполняю:\n`{nlp_command}`\n\n{output}"
            log_telegram_message(f"Outgoing NLP response: {reply_text}")
            bot.send_message(chat_id, reply_text, parse_mode="Markdown")
            return

        # If not an NLP command or keyword, try to parse as JSON (old behavior)
        log_local_bot_event(f"No NLP command or keyword matched for '{text}'. Attempting JSON parse.")
        try:
            # Ensure to use original `text` for JSON parsing, not `text_lower`
            command_data = json.loads(text)
            command_text_for_log = text # Store original text for logging validation errors
        except json.JSONDecodeError:
            # Default echo response if not JSON, NLP, or keyword
            reply_text = f"Ты сказал: {text}"
            log_telegram_message(f"Not JSON, NLP, or keyword. Outgoing echo: {reply_text}")
            bot.reply_to(message, reply_text)
            log_local_bot_event(f"Invalid JSON, not NLP, and not a keyword from {chat_id}: {text}")
            return

        # --- Existing JSON command processing logic starts here ---
        log_local_bot_event(f"Attempting to process as JSON command from {chat_id}: {text}")
    else: # If it starts with '/', and wasn't handled by a command handler, it's an unknown command
        if not any(cmd_handler.filters.get('commands') and text.split('@')[0] in ['/'+c for c in cmd_handler.filters['commands']] for cmd_handler in bot.message_handlers if isinstance(cmd_handler, telebot.handler_backends.CommandHandler) and cmd_handler.filters.get('commands')):
            reply_text = f"Неизвестная команда: {text}"
            log_telegram_message(f"Unknown command: {text} from {chat_id}. Outgoing: {reply_text}")
            bot.reply_to(message, reply_text)
        # If it was a known command, it's already handled, so we do nothing here.
        return
    required_fields = {
        "type": str,
        "module": str,
        "args": dict,
        "id": (str, int)
    }

    for field, expected_type in required_fields.items():
        if field not in command_data:
            error_msg = f"Error: Missing required field '{field}'."
            log_telegram_message(f"Outgoing JSON validation error: {error_msg}")
            bot.reply_to(message, error_msg)
            log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text_for_log})")
            return
        if field == "id":
            if not any(isinstance(command_data[field], t) for t in expected_type):
                error_msg = f"Error: Field '{field}' must be type {' or '.join(t.__name__ for t in expected_type)}. Got value '{command_data[field]}' of type {type(command_data[field]).__name__}."
                log_telegram_message(f"Outgoing JSON validation error: {error_msg}")
                bot.reply_to(message, error_msg)
                log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text_for_log})")
                return
        elif not isinstance(command_data[field], expected_type):
            error_msg = f"Error: Field '{field}' must be type {expected_type.__name__}. Got value '{command_data[field]}' of type {type(command_data[field]).__name__}."
            log_telegram_message(f"Outgoing JSON validation error: {error_msg}")
            bot.reply_to(message, error_msg)
            log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text_for_log})")
            return

    if not command_data['module'].strip():
        error_msg = f"Error: Field 'module' must be a non-empty string. Got value '{command_data['module']}'."
        log_telegram_message(f"Outgoing JSON validation error: {error_msg}")
        bot.reply_to(message, error_msg)
        log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text_for_log})")
        return

    if not command_data['type'].strip():
        error_msg = f"Error: Field 'type' must be a non-empty string. Got value '{command_data['type']}'."
        log_telegram_message(f"Outgoing JSON validation error: {error_msg}")
        bot.reply_to(message, error_msg)
        log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text_for_log})")
        return

    log_local_bot_event(f"Successfully validated JSON command from {chat_id}: {json.dumps(command_data)}")

    command_type = command_data.get("type")
    reply_text_json = "" # For logging JSON command replies

    if command_type == "log_event":
        handle_log_event(command_data, chat_id)
        reply_text_json = "✅ 'log_event' processed (placeholder)."
        bot.reply_to(message, reply_text_json)
    elif command_type == "mind_clearing":
        handle_mind_clearing(command_data, chat_id)
        reply_text_json = "✅ 'mind_clearing' processed (placeholder)."
        bot.reply_to(message, reply_text_json)
    else:
        log_local_bot_event(f"JSON Command type '{command_type}' not specifically handled, proceeding with default save. Full command data: {json.dumps(command_data)}")
        timestamp_str = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
        command_file_name = f"{timestamp_str}_{chat_id}.json"
        module_name = command_data.get('module', 'telegram_general')
        module_command_dir = COMMAND_FILE_DIR / f"telegram_mod_{module_name}" if module_name != 'telegram_general' else COMMAND_FILE_DIR / 'telegram_general'
        module_command_dir.mkdir(parents=True, exist_ok=True)
        command_file_path = module_command_dir / command_file_name

        with open(command_file_path, "w", encoding="utf-8") as f:
            json.dump(command_data, f, ensure_ascii=False, indent=2)

        reply_text_json = f"✅ JSON Command received and saved as `{command_file_path}`."
        bot.reply_to(message, reply_text_json)
        log_local_bot_event(f"Saved JSON command from {chat_id} to {command_file_path}")

    if reply_text_json: # Log the reply for JSON commands
        log_telegram_message(f"Outgoing JSON command response: {reply_text_json}")


if __name__ == '__main__':
    log_local_bot_event("Bot starting...")
    try:
        bot.polling(none_stop=False) # none_stop=False allows bot.stop_polling() to work
    except Exception as e:
        log_local_bot_event(f"Bot polling crashed with exception: {e}")
    finally:
        log_local_bot_event("Bot stopped or crashed.")
