import telebot
import json
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
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
LOG_DIR = Path('logs')
LOG_DIR.mkdir(parents=True, exist_ok=True)
TELEGRAM_LOG_FILE = LOG_DIR / 'telegram.log'

def get_utc_now():
    """Returns the current UTC datetime, timezone-aware."""
    return datetime.now(timezone.utc)

def log_to_file(message, filename=TELEGRAM_LOG_FILE):
    """Appends a message to the specified log file."""
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(f"{get_utc_now().isoformat()} | {message}\n")

def log_local_bot_event(message):
    """Logs an event to the console and to the telegram.log file."""
    print(f"[BOT EVENT] {get_utc_now().isoformat()}: {message}")
    log_to_file(f"[BOT_EVENT] {message}")

# --- Bot State & Cache Setup ---
BOT_START_TIME = get_utc_now()
CACHE = {}
CACHE_TTL_SECONDS = 60 # Time-to-live for cache entries, e.g., 60 seconds
CACHE_STATS = {"hits": 0, "misses": 0}

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

# --- /start and /help Commands ---
COMMAND_DESCRIPTIONS = {
    "/start": "Показать приветственное сообщение и список команд.",
    "/help": "Показать это сообщение помощи и список команд.",
    "/status": "Показать статус бота и статистику кеша (если применимо)."
    # Add other explicit slash commands here as they are implemented
}

NLP_EXAMPLES = [
    "'покажи место на диске'",
    "'какой аптайм у сервера?' (или 'аптайм подробно' для другого формата)",
    "'сколько памяти свободно?'",
    "'кто я?' / 'какой пользователь?'",
    "'какое сегодня число и время?'",
    "'какая загрузка процессора?'",
    "'покажи список файлов'"
]

def get_help_message():
    """Generates the help message dynamically."""
    message_lines = [
        "Привет! Я ваш бот-помощник Katana.",
        "Вот что я могу делать:",
        "",
        "**Основные команды:**"
    ]
    for command, description in COMMAND_DESCRIPTIONS.items():
        message_lines.append(f"{command} - {description}")

    message_lines.extend([
        "",
        "**Примеры текстовых команд (NLP):**",
        "Вы можете использовать фразы для получения информации о системе, например:",
    ])
    message_lines.extend([f"- {example}" for example in NLP_EXAMPLES])

    message_lines.extend([
        "",
        "**JSON-команды:**",
        "Я также могу обрабатывать команды в формате JSON для более сложных задач.",
        "Например: `{\"type\": \"log_event\", \"module\": \"system\", \"args\": {\"event_details\": \"...\"}, \"id\": \"cmd123\"}`"
    ])
    return "\n".join(message_lines)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    log_local_bot_event(f"/start command received from {message.chat.id}")
    bot.reply_to(message, get_help_message(), parse_mode="Markdown")

@bot.message_handler(commands=['help'])
def send_help(message):
    log_local_bot_event(f"/help command received from {message.chat.id}")
    bot.reply_to(message, get_help_message(), parse_mode="Markdown")

# --- /status Command ---
@bot.message_handler(commands=['status'])
def send_status(message):
    log_local_bot_event(f"/status command received from {message.chat.id}")

    # Bot uptime
    uptime_delta = get_utc_now() - BOT_START_TIME
    # Format timedelta to a more readable string (e.g., "X days, HH:MM:SS")
    days = uptime_delta.days
    hours, remainder = divmod(uptime_delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{days}д, {hours:02}ч:{minutes:02}м:{seconds:02}с"

    # Cache stats
    active_cache_items = 0
    current_time = get_utc_now()
    for cmd, data in list(CACHE.items()): # Iterate over a copy for safe removal
        if (current_time - data['timestamp']).total_seconds() >= CACHE_TTL_SECONDS:
            # Optional: Clean up expired items during status check, or rely on overwrite
            # del CACHE[cmd]
            # log_local_bot_event(f"Expired cache item '{cmd}' removed during status check.")
            pass # Just counting active ones
        else:
            active_cache_items += 1

    total_cache_items = len(CACHE) # Total including expired but not yet overwritten

    status_message = (
        f"🤖 **Статус Бота** 🤖\n"
        f"Время работы: {uptime_str}\n"
        f"\n"
        f"**Кеш:**\n"
        f"TTL записей: {CACHE_TTL_SECONDS} секунд\n"
        f"Активных записей в кеше: {active_cache_items}\n"
        f"Всего записей в кеше (включая устаревшие): {total_cache_items}\n"
        f"Попаданий в кеш: {CACHE_STATS['hits']}\n"
        f"Промахов кеша: {CACHE_STATS['misses']}"
    )
    bot.reply_to(message, status_message, parse_mode="Markdown")

# This will be the new text handler
@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text_message(message):
    """Handles incoming text messages, attempting NLP interpretation first."""
    chat_id = message.chat.id
    text = message.text

    log_local_bot_event(f"Received text message from {chat_id}: {text}")

    # Attempt to interpret the text as a natural language command
    # Define cacheable NLP commands here (actual command string executed)
    CACHEABLE_NLP_COMMANDS = {
        "df -h",    # Disk space
        "uptime",   # System uptime (traditional format)
        "uptime -p",# System uptime (pretty format)
        "free -m",  # Memory usage (in MB)
        "whoami",   # Current user
        "date",     # Current date and time
        # "top -n1 | head -5" # CPU usage is too volatile for default 60s cache
    }

    nlp_command_interpretation = interpret(text) # Renamed to avoid confusion with nlp_command variable used later

    if nlp_command_interpretation:
        nlp_command = nlp_command_interpretation # Assign to nlp_command for use
        log_to_file(f'[NLU] "{text}" → "{nlp_command}"') # Logging interpretation

        output = ""
        cache_hit = False

        if nlp_command in CACHEABLE_NLP_COMMANDS:
            current_time = get_utc_now()
            if nlp_command in CACHE and \
               (current_time - CACHE[nlp_command]['timestamp']).total_seconds() < CACHE_TTL_SECONDS:
                output = CACHE[nlp_command]['output']
                cache_hit = True
                CACHE_STATS["hits"] += 1
                log_local_bot_event(f"Cache hit for command: {nlp_command}. Total hits: {CACHE_STATS['hits']}")
            else:
                output = run_katana_command(nlp_command)
                CACHE[nlp_command] = {'output': output, 'timestamp': current_time}
                CACHE_STATS["misses"] += 1
                log_local_bot_event(f"Cache miss for command: {nlp_command}. Executed and cached. Total misses: {CACHE_STATS['misses']}")
        else:
            # Not a cacheable command, execute directly
            output = run_katana_command(nlp_command)

        reply_message = f"🧠 Понял. Выполняю:\n`{nlp_command}`"
        if cache_hit:
            reply_message += " (из кеша)"
        reply_message += f"\n\n{output}"

        bot.send_message(chat_id, reply_message, parse_mode="Markdown")
        return

    # If not an NLP command, try to parse as JSON (old behavior)
    log_local_bot_event(f"No NLP command interpreted from '{text}'. Attempting JSON parse.")
    try:
        command_data = json.loads(text)
        # If JSON parsing succeeds, pass to the dedicated JSON processor
        _process_json_command(command_data, message, text) # text is for logging original command
    except json.JSONDecodeError:
        # If it's not JSON either, then it's an unrecognized command
        unrecognized_command_message = (
            "🤖 Не понял команду. Я могу выполнять некоторые текстовые команды (например, 'покажи место на диске') "
            "или принимать команды в формате JSON. \n\nДля списка доступных команд, попробуй /help."
        )
        bot.reply_to(message, unrecognized_command_message)
        log_local_bot_event(f"Unrecognized command (not NLP, not valid JSON) from {chat_id}: {text}")
        return

def _process_json_command(command_data, message, original_command_text):
    """Validates, routes, and processes a parsed JSON command."""
    chat_id = message.chat.id

    # Validate command_data fields
    required_fields = {
        "type": str,
        "module": str,
        "args": dict,
        "id": (str, int)  # id can be string or integer
    }

    for field, expected_type in required_fields.items():
        if field not in command_data:
            error_msg = f"Ошибка валидации JSON: Отсутствует обязательное поле '{field}'."
            bot.reply_to(message, error_msg)
            log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {original_command_text})")
            return
        if field == "id":
            if not any(isinstance(command_data[field], t) for t in expected_type):
                error_msg = f"Ошибка валидации JSON: Поле '{field}' должно быть типа {' или '.join(t.__name__ for t in expected_type)}. Получено значение '{command_data[field]}' типа {type(command_data[field]).__name__}."
                bot.reply_to(message, error_msg)
                log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {original_command_text})")
                return
        elif not isinstance(command_data[field], expected_type):
            error_msg = f"Ошибка валидации JSON: Поле '{field}' должно быть типа {expected_type.__name__}. Получено значение '{command_data[field]}' типа {type(command_data[field]).__name__}."
            bot.reply_to(message, error_msg)
            log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {original_command_text})")
            return

    if not command_data['module'].strip():
        error_msg = f"Ошибка валидации JSON: Поле 'module' не должно быть пустым. Получено значение '{command_data['module']}'."
        bot.reply_to(message, error_msg)
        log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {original_command_text})")
        return

    if not command_data['type'].strip():
        error_msg = f"Ошибка валидации JSON: Поле 'type' не должно быть пустым. Получено значение '{command_data['type']}'."
        bot.reply_to(message, error_msg)
        log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {original_command_text})")
        return

    log_local_bot_event(f"Successfully validated JSON command from {chat_id}: {json.dumps(command_data)}")

    command_type = command_data.get("type")
    if command_type == "log_event":
        handle_log_event(command_data, chat_id)
        bot.reply_to(message, "✅ 'log_event' processed (placeholder).")
        return
    elif command_type == "mind_clearing":
        handle_mind_clearing(command_data, chat_id)
        bot.reply_to(message, "✅ 'mind_clearing' processed (placeholder).")
        return

    log_local_bot_event(f"Command type '{command_type}' not specifically handled, proceeding with default save. Full command data: {json.dumps(command_data)}")

    timestamp_str = get_utc_now().strftime('%Y%m%d_%H%M%S_%f')
    command_file_name = f"{timestamp_str}_{chat_id}.json"
    module_name = command_data.get('module', 'telegram_general')
    module_command_dir = COMMAND_FILE_DIR / f"telegram_mod_{module_name}" if module_name != 'telegram_general' else COMMAND_FILE_DIR / 'telegram_general'
    module_command_dir.mkdir(parents=True, exist_ok=True)
    command_file_path = module_command_dir / command_file_name

    with open(command_file_path, "w", encoding="utf-8") as f:
        json.dump(command_data, f, ensure_ascii=False, indent=2)

    bot.reply_to(message, f"✅ Command received and saved as `{command_file_path}`.")
    log_local_bot_event(f"Saved command from {chat_id} to {command_file_path}")

if __name__ == '__main__':
    log_local_bot_event("Bot starting...")
    bot.polling()
    log_local_bot_event("Bot stopped.")
