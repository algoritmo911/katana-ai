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
LOG_DIR = Path('logs')
LOG_DIR.mkdir(parents=True, exist_ok=True)
TELEGRAM_LOG_FILE = LOG_DIR / 'telegram.log'

def log_to_file(message, filename=TELEGRAM_LOG_FILE):
    """Appends a message to the specified log file."""
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.utcnow().isoformat()} | {message}\n")

def log_local_bot_event(message):
    """Logs an event to the console and to the telegram.log file."""
    print(f"[BOT EVENT] {datetime.utcnow().isoformat()}: {message}")
    log_to_file(f"[BOT_EVENT] {message}")

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
        # Check if stderr is empty or provides a generic "not found" type error
        stderr_output = e.stderr.strip()
        if "not found" in stderr_output.lower() or "no such file" in stderr_output.lower():
            error_message = f"⚠️ Команда '{command}' не найдена или не может быть исполнена."
        elif stderr_output:
            error_message = f"🚫 Ошибка при выполнении команды '{command}':\n`{stderr_output}`"
        else:
            error_message = f"🚫 Ошибка при выполнении команды '{command}' (код возврата: {e.returncode})."
        log_local_bot_event(error_message)
        return error_message
    except subprocess.TimeoutExpired:
        error_message = f"⏳ Команда '{command}' выполнялась слишком долго и была остановлена."
        log_local_bot_event(error_message)
        return error_message
    except Exception as e:
        error_message = f"💥 Произошла непредвиденная ошибка при выполнении команды '{command}': {str(e)}"
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

# This will be the new text handler
@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text_message(message):
    """Handles incoming text messages, attempting NLP interpretation first."""
    chat_id = message.chat.id
    text = message.text

    log_local_bot_event(f"Received text message from {chat_id}: {text}")

    # Attempt to interpret the text as a natural language command
    nlp_command = interpret(text)

    if nlp_command:
        log_to_file(f'[NLU] "{text}" → "{nlp_command}"') # Logging interpretation
        output = run_katana_command(nlp_command)
        bot.send_message(chat_id, f"🧠 Понял. Выполняю:\n`{nlp_command}`\n\n{output}", parse_mode="Markdown")
        return

    # If not an NLP command, try to parse as JSON (old behavior)
    log_local_bot_event(f"No NLP command interpreted from '{text}'. Attempting JSON parse.")
    try:
        command_data = json.loads(text)
    except json.JSONDecodeError:
        # If it's not JSON either, then it's an unrecognized command
        bot.reply_to(message, "🤖 Не понял команду. Попробуй переформулировать или отправь JSON-команду.")
        log_local_bot_event(f"Invalid JSON and not an NLP command from {chat_id}: {text}")
        return

    # --- Existing JSON command processing logic starts here ---
    # (Copied and adapted from the original handle_message)
    # log_local_bot_event(f"Attempting to process as JSON command from {chat_id}: {text}") # Already logged above
    # Validate command_data fields
    required_fields = {
        "type": str,
        "module": str,
        "args": dict,
        "id": (str, int)  # id can be string or integer
    }

    for field, expected_type in required_fields.items():
        if field not in command_data:
            error_msg = f"Ошибка: отсутствует обязательное поле '{field}'."
            bot.reply_to(message, error_msg)
            log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Original Text: {text})")
            return
        # isinstance check for the field's type
        # For 'id', it can be str or int. For others, it's a single type.
        if field == "id":
            if not any(isinstance(command_data[field], t) for t in expected_type):
                type_names = ' или '.join(t.__name__ for t in expected_type)
                error_msg = f"Ошибка: поле '{field}' должно быть типа {type_names}. Получено значение '{command_data[field]}' типа {type(command_data[field]).__name__}."
                bot.reply_to(message, error_msg)
                log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Original Text: {text})")
                return
        elif not isinstance(command_data[field], expected_type):
            error_msg = f"Ошибка: поле '{field}' должно быть типа {expected_type.__name__}. Получено значение '{command_data[field]}' типа {type(command_data[field]).__name__}."
            bot.reply_to(message, error_msg)
            log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Original Text: {text})")
            return

    # Additional validation for 'module' and 'type' fields
    if not command_data['module'].strip():
        error_msg = f"Ошибка: поле 'module' должно быть непустой строкой. Получено значение '{command_data['module']}'."
        bot.reply_to(message, error_msg)
        log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Original Text: {text})")
        return

    if not command_data['type'].strip():
        error_msg = f"Ошибка: поле 'type' должно быть непустой строкой. Получено значение '{command_data['type']}'."
        bot.reply_to(message, error_msg)
        log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Original Text: {text})")
        return

    # Log successful validation
    log_local_bot_event(f"Successfully validated command from {chat_id}: {json.dumps(command_data)}")

    # Command routing based on 'type'
    command_type = command_data.get("type")

    if command_type == "log_event":
        handle_log_event(command_data, chat_id)
        bot.reply_to(message, "✅ Команда 'log_event' обработана (заглушка).")
        return
    elif command_type == "mind_clearing":
        handle_mind_clearing(command_data, chat_id)
        bot.reply_to(message, "✅ Команда 'mind_clearing' обработана (заглушка).")
        return

    # If type is not matched, proceed with default behavior (saving)
    log_local_bot_event(f"Command type '{command_type}' not specifically handled, proceeding with default save. Full command data: {json.dumps(command_data)}")

    # Save the command to a file
    log_local_bot_event(f"Attempting to save command from {chat_id}. Full command data: {json.dumps(command_data)}")
    timestamp_str = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
    command_file_name = f"{timestamp_str}_{chat_id}.json"

    module_name = command_data.get('module', 'telegram_general')
    module_command_dir = COMMAND_FILE_DIR / f"telegram_mod_{module_name}" if module_name != 'telegram_general' else COMMAND_FILE_DIR / 'telegram_general'
    module_command_dir.mkdir(parents=True, exist_ok=True)
    command_file_path = module_command_dir / command_file_name

    with open(command_file_path, "w", encoding="utf-8") as f:
        json.dump(command_data, f, ensure_ascii=False, indent=2)

    bot.reply_to(message, f"✅ JSON-команда получена и сохранена как `{command_file_path}`.")
    log_local_bot_event(f"Saved command from {chat_id} to {command_file_path}")

if __name__ == '__main__':
    log_local_bot_event("Bot starting...")
    bot.polling()
    log_local_bot_event("Bot stopped.")
