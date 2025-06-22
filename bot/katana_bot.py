import telebot
import json
import os
from pathlib import Path
from datetime import datetime

# Получаем токен из переменной окружения
API_TOKEN = os.getenv('KATANA_TELEGRAM_TOKEN', 'YOUR_API_TOKEN')
if not API_TOKEN or ':' not in API_TOKEN:
    raise ValueError("❌ Invalid or missing Telegram API token. Please set KATANA_TELEGRAM_TOKEN env variable with format '123456:ABCDEF'.")

bot = telebot.TeleBot(API_TOKEN)

# Папка для сохранения команд
COMMAND_FILE_DIR = Path('commands')
COMMAND_FILE_DIR.mkdir(parents=True, exist_ok=True)

def log_local_bot_event(message):
    """Вывод лога события в консоль."""
    print(f"[BOT EVENT] {datetime.utcnow().isoformat()}: {message}")

def handle_log_event(command_data, chat_id):
    """Обработка команды 'log_event' (заглушка)."""
    log_local_bot_event(f"handle_log_event called for chat_id {chat_id} with data: {command_data}")

def handle_mind_clearing(command_data, chat_id):
    """Обработка команды 'mind_clearing' (заглушка)."""
    log_local_bot_event(f"handle_mind_clearing called for chat_id {chat_id} with data: {command_data}")

# --- Start of refactored functions ---

def parse_command(command_text: str) -> tuple[dict | None, str | None]:
    """
    Parses the JSON command string.
    Returns a tuple: (parsed_data, error_message).
    If parsing is successful, error_message is None.
    If parsing fails, parsed_data is None.
    """
    try:
        command_data = json.loads(command_text)
        return command_data, None
    except json.JSONDecodeError:
        return None, "Invalid JSON format."

def validate_command(command_data: dict) -> str | None:
    """
    Validates the structure and types of the command data.
    Returns an error message string if validation fails, None otherwise.
    """
    required_fields = {
        "type": str,
        "module": str,
        "args": dict,
        "id": (str, int)
    }

    for field, expected_type in required_fields.items():
        if field not in command_data:
            return f"Missing required field '{field}'."

        # Special handling for 'id' which can be str or int
        if field == "id":
            if not any(isinstance(command_data[field], t) for t in expected_type):
                return f"Field '{field}' must be type str or int. Got {type(command_data[field]).__name__}."
        elif not isinstance(command_data[field], expected_type):
            return f"Field '{field}' must be type {expected_type.__name__}. Got {type(command_data[field]).__name__}."
    return None

def route_command(command_data: dict, message: telebot.types.Message, chat_id: int) -> bool:
    """
    Checks the command type and calls the appropriate handler.
    Returns True if a specific handler was called, False otherwise.
    """
    command_type = command_data.get("type")

    if command_type == "log_event":
        handle_log_event(command_data, chat_id)
        bot.reply_to(message, "✅ 'log_event' processed (placeholder).")
        return True
    elif command_type == "mind_clearing":
        handle_mind_clearing(command_data, chat_id)
        bot.reply_to(message, "✅ 'mind_clearing' processed (placeholder).")
        return True

    return False

def save_command_to_file(command_data: dict, chat_id: int) -> Path:
    """
    Saves the command to a JSON file.
    Returns the path to the saved file.
    """
    timestamp_str = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
    command_file_name = f"{timestamp_str}_{chat_id}.json"
    
    module_name = command_data.get('module', 'telegram_general')
    # Ensure module_name is a string and sanitize it (allow alphanumeric and underscores)
    if not isinstance(module_name, str) or not module_name or not all(c.isalnum() or c == '_' for c in module_name):
        module_name = 'telegram_general' # Default to general if invalid or empty

    module_command_dir = COMMAND_FILE_DIR / f"telegram_mod_{module_name}" if module_name != 'telegram_general' else COMMAND_FILE_DIR / 'telegram_general'
    module_command_dir.mkdir(parents=True, exist_ok=True)
    command_file_path = module_command_dir / command_file_name

    with open(command_file_path, "w", encoding="utf-8") as f:
        json.dump(command_data, f, ensure_ascii=False, indent=2)
    
    return command_file_path

# --- End of refactored functions ---

@bot.message_handler(commands=['start'])
def handle_start(message):
    """Ответ на /start"""
    bot.reply_to(message, "Привет! Я — Katana. Отправь JSON-команду, чтобы начать.")
    log_local_bot_event(f"/start received from {message.chat.id}")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Главный обработчик входящих сообщений."""
    chat_id = message.chat.id
    command_text = message.text

    log_local_bot_event(f"Received message from {chat_id}: {command_text}")

    # 1. Parse command
    command_data, error_msg = parse_command(command_text)
    if error_msg:
        bot.reply_to(message, f"❌ Error: {error_msg}")
        log_local_bot_event(f"Parsing failed for {chat_id}: {error_msg} (Command: {command_text})")
        return

    # Ensure command_data is not None, though parse_command should always return a dict or None with an error
    if command_data is None: # Should not happen if error_msg is handled
        bot.reply_to(message, "❌ Error: Unknown parsing error.")
        log_local_bot_event(f"Unknown parsing error for {chat_id}: {command_text}")
        return

    # 2. Validate command
    error_msg = validate_command(command_data)
    if error_msg:
        bot.reply_to(message, f"❌ Error: {error_msg}")
        log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {json.dumps(command_data)})")
        return

    # 3. Route command to specific handlers
    if route_command(command_data, message, chat_id):
        # Command was handled by a specific route, reply is done in route_command
        return

    # 4. Default: Save command to file if not handled by a specific route
    log_local_bot_event(f"Command type '{command_data.get('type')}' not specifically handled, proceeding with default save.")
    try:
        saved_file_path = save_command_to_file(command_data, chat_id)
        bot.reply_to(message, f"✅ Command received and saved as `{saved_file_path}`.")
        log_local_bot_event(f"Saved command from {chat_id} to {saved_file_path}")
    except Exception as e:
        bot.reply_to(message, "❌ Error: Could not save command.")
        log_local_bot_event(f"Error saving command for {chat_id} from {json.dumps(command_data)}: {e}")

if __name__ == '__main__':
    log_local_bot_event("Bot starting...")
    bot.polling()
    log_local_bot_event("Bot stopped.")