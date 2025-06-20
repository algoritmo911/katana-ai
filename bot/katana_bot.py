import telebot
import json
import os
from pathlib import Path
from datetime import datetime, timezone # Added timezone
import threading # Added threading
from flask import Flask, jsonify, request # Added Flask imports
from flask_cors import CORS # Added Flask-CORS

# Получаем токен из переменной окружения
API_TOKEN = os.getenv('KATANA_TELEGRAM_TOKEN', 'YOUR_API_TOKEN')
if not API_TOKEN or ':' not in API_TOKEN:
    raise ValueError("❌ Invalid or missing Telegram API token. Please set KATANA_TELEGRAM_TOKEN env variable with format '123456:ABCDEF'.")

bot = telebot.TeleBot(API_TOKEN)

# Папка для сохранения команд
COMMAND_FILE_DIR = Path('commands')
COMMAND_FILE_DIR.mkdir(parents=True, exist_ok=True)
API_COMMAND_FILE_DIR = COMMAND_FILE_DIR / 'api_commands' # Separate subdir for API commands
API_COMMAND_FILE_DIR.mkdir(parents=True, exist_ok=True)

MAX_LOG_ENTRIES = 100 # Max number of log entries to keep in memory
bot_logs = []
log_lock = threading.Lock() # To ensure thread-safe access to bot_logs

# --- Start of new Flask App Setup ---
flask_app = Flask(__name__)
CORS(flask_app, resources={r"/api/*": {"origins": "http://localhost:5173"}}) # Allow UI dev server

# Record bot start time for uptime calculation
bot_start_time = datetime.now(timezone.utc)

@flask_app.route('/api/', methods=['GET'])
def api_root():
    return jsonify({"message": "Katana Bot API is running"}), 200

@flask_app.route('/api/status', methods=['GET'])
def api_status():
    try:
        # Calculate uptime
        uptime_delta = datetime.now(timezone.utc) - bot_start_time
        total_seconds = int(uptime_delta.total_seconds())
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"

        # Get Telegram bot polling status (simplified)
        # Actual polling status might be harder to get directly from pyTelegramBotAPI instance state
        # without custom tracking. For now, if the API server is up, assume bot is trying to poll.
        # A more robust check might involve a custom flag updated by bot's polling loop.
        tg_bot_status = "Polling (Assumed)"
        # A more direct check like `bot.is_polling` does not exist in standard pyTelegramBotAPI.
        # We could also try to get bot info as a health check:
        # try:
        #     bot_info = bot.get_me()
        #     tg_bot_status = f"Connected as @{bot_info.username}"
        # except Exception as e:
        #     log_local_bot_event(f"Could not get bot info for status: {e}")
        #     tg_bot_status = "Connection issue?"


        status_data = {
            "status": "Online", # API server status
            "uptime": uptime_str,
            "ping": "N/A", # Placeholder for actual ping logic if needed later
            "bot_status": tg_bot_status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return jsonify(status_data), 200
    except Exception as e:
        log_local_bot_event(f"Error in /api/status: {e}", level="ERROR", module="api_status")
        return jsonify({"success": False, "error": "Failed to retrieve status", "details": str(e)}), 500

@flask_app.route('/api/logs', methods=['GET'])
def api_logs():
    try:
        # Get query parameters for filtering
        filter_level = request.args.get('level', type=str)
        filter_module = request.args.get('module', type=str)

        with log_lock: # Ensure thread-safe access to bot_logs
            # Make a copy for safe iteration if filtering modifies the list
            # or if new logs could be added during iteration by another thread.
            # Here, simple read access is likely fine, but copying is safer.
            logs_to_return = list(bot_logs)

        if filter_level:
            logs_to_return = [log for log in logs_to_return if log['level'].upper() == filter_level.upper()]

        if filter_module:
            logs_to_return = [log for log in logs_to_return if log['module'].lower() == filter_module.lower()] # Case-insensitive module filter

        return jsonify(logs_to_return), 200
    except Exception as e:
        # Use the existing log_local_bot_event for logging errors in API endpoints
        log_local_bot_event(f"Error in /api/logs: {e}", level="ERROR", module="api_logs")
        return jsonify({"success": False, "error": "Failed to retrieve logs", "details": str(e)}), 500

@flask_app.route('/api/command', methods=['POST'])
def api_command():
    try:
        if not request.is_json:
            log_local_bot_event("Request to /api/command is not JSON", level="WARN", module="api_command")
            return jsonify({"success": False, "error": "Invalid request: Content-Type must be application/json"}), 415 # Unsupported Media Type

        command_data = request.get_json()
        log_local_bot_event(f"Received command via /api/command: {command_data}", module="api_command")

        # Validate required fields (similar to Telegram handler)
        required_fields = {
            "type": str,
            "module": str,
            "args": dict, # Assuming args will also be part of the command from UI
            "id": (str, int)
        }

        missing_fields = [field for field in required_fields if field not in command_data]
        if missing_fields:
            error_msg = f"Missing required field(s): {', '.join(missing_fields)}"
            log_local_bot_event(error_msg, level="WARN", module="api_command")
            return jsonify({"success": False, "error": error_msg}), 400 # Bad Request

        for field, expected_type in required_fields.items():
            # Special handling for 'id' which can be str or int
            if field == "id":
                if not isinstance(command_data[field], expected_type): # expected_type is (str, int)
                    error_msg = f"Field '{field}' must be type str or int. Got {type(command_data[field]).__name__}."
                    log_local_bot_event(error_msg, level="WARN", module="api_command")
                    return jsonify({"success": False, "error": error_msg}), 400
            elif not isinstance(command_data[field], expected_type):
                error_msg = f"Field '{field}' must be type {expected_type.__name__}. Got {type(command_data[field]).__name__}."
                log_local_bot_event(error_msg, level="WARN", module="api_command")
                return jsonify({"success": False, "error": error_msg}), 400

        # Process the command (e.g., save to file)
        timestamp_str = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
        # Use a generic identifier for API commands, or could use command_data['id'] if suitable
        command_file_name = f"api_{timestamp_str}_{command_data.get('id', 'unknown_id')}.json"

        # Save in a specific subdirectory for API commands
        module_name = command_data.get('module', 'general_api')
        # Use API_COMMAND_FILE_DIR
        module_command_dir = API_COMMAND_FILE_DIR / f"mod_{module_name}"
        module_command_dir.mkdir(parents=True, exist_ok=True)
        command_file_path = module_command_dir / command_file_name

        with open(command_file_path, "w", encoding="utf-8") as f:
            json.dump(command_data, f, ensure_ascii=False, indent=2)

        log_local_bot_event(f"API Command saved to {command_file_path}", module="api_command")

        # For now, we don't execute it directly like Telegram commands, just save.
        # Future: Could have a dispatch mechanism here.

        return jsonify({"success": True, "message": "Command received and saved.", "file_path": str(command_file_path)}), 200

    except Exception as e:
        log_local_bot_event(f"Error in /api/command: {e}", level="ERROR", module="api_command")
        # It's good to avoid sending detailed internal error messages to the client in production.
        return jsonify({"success": False, "error": "Failed to process command due to an internal error."}), 500

# --- End of new Flask App Setup ---


def log_local_bot_event(message, level="INFO", module="system"):
    # Вывод лога события в консоль и сохранение в памяти.
    timestamp = datetime.now(timezone.utc).isoformat()
    log_entry = {
        "timestamp": timestamp,
        "level": level.upper(),
        "module": module,
        "message": message
    }

    # Print to console (original behavior, but with new formatting)
    print(f"[{log_entry['level']}] [BOT EVENT] {timestamp} [{module}]: {message}")

    # Store in memory with thread safety
    with log_lock:
        bot_logs.append(log_entry)
        if len(bot_logs) > MAX_LOG_ENTRIES:
            # Keep only the most recent MAX_LOG_ENTRIES logs
            bot_logs[:] = bot_logs[-MAX_LOG_ENTRIES:]

def handle_log_event(command_data, chat_id):
    """Обработка команды 'log_event' (заглушка)."""
    log_local_bot_event(f"handle_log_event called for chat_id {chat_id} with data: {command_data}", module="telegram_handler")

def handle_mind_clearing(command_data, chat_id):
    """Обработка команды 'mind_clearing' (заглушка)."""
    log_local_bot_event(f"handle_mind_clearing called for chat_id {chat_id} with data: {command_data}", module="telegram_handler")

@bot.message_handler(commands=['start'])
def handle_start(message):
    """Ответ на /start"""
    bot.reply_to(message, "Привет! Я — Katana. Отправь JSON-команду, чтобы начать.")
    log_local_bot_event(f"/start received from {message.chat.id}", module="telegram_handler")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Главный обработчик входящих сообщений."""
    chat_id = message.chat.id
    command_text = message.text

    log_local_bot_event(f"Received message from {chat_id}: {command_text}", module="telegram_handler")

    try:
        command_data = json.loads(command_text)
    except json.JSONDecodeError:
        bot.reply_to(message, "❌ Error: Invalid JSON format.")
        log_local_bot_event(f"Invalid JSON from {chat_id}: {command_text}", level="WARN", module="telegram_handler")
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
            log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text})", level="WARN", module="telegram_handler")
            return
        if field == "id":
            if not any(isinstance(command_data[field], t) for t in expected_type):
                error_msg = f"❌ Error: Field '{field}' must be type str or int. Got {type(command_data[field]).__name__}."
                bot.reply_to(message, error_msg)
                log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text})", level="WARN", module="telegram_handler")
                return
        elif not isinstance(command_data[field], expected_type):
            error_msg = f"❌ Error: Field '{field}' must be type {expected_type.__name__}. Got {type(command_data[field]).__name__}."
            bot.reply_to(message, error_msg)
            log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text})", level="WARN", module="telegram_handler")
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

    log_local_bot_event(f"Command type '{command_type}' not specifically handled, proceeding with default save.", module="telegram_handler")

    timestamp_str = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
    command_file_name = f"{timestamp_str}_{chat_id}.json"
    
    module_name = command_data.get('module', 'telegram_general')
    module_command_dir = COMMAND_FILE_DIR / f"telegram_mod_{module_name}" if module_name != 'telegram_general' else COMMAND_FILE_DIR / 'telegram_general'
    module_command_dir.mkdir(parents=True, exist_ok=True)
    command_file_path = module_command_dir / command_file_name

    with open(command_file_path, "w", encoding="utf-8") as f:
        json.dump(command_data, f, ensure_ascii=False, indent=2)
    
    bot.reply_to(message, f"✅ Command received and saved as `{command_file_path}`.")
    log_local_bot_event(f"Saved command from {chat_id} to {command_file_path}", module="telegram_handler")

# --- Main execution block modification ---
def run_flask_app():
    # Use a production-ready server if deploying, e.g., waitress or gunicorn
    # For development, Flask's built-in server is fine but run it on a specific port
    # and disable debug mode for threaded execution if it causes issues.
    # Host 0.0.0.0 to make it accessible from outside Docker if needed, though for UI localhost is fine.
    flask_app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)

if __name__ == '__main__':
    log_local_bot_event("Bot starting...", module="init")

    # Start Flask app in a new thread
    log_local_bot_event("Starting Flask API server...", module="init")
    flask_thread = threading.Thread(target=run_flask_app, daemon=True)
    flask_thread.start()
    log_local_bot_event("Flask API server started in a separate thread.", module="init")

    # Start Telegram bot polling in the main thread
    try:
        bot.polling(none_stop=True) # none_stop=True to keep it running
    except Exception as e:
        log_local_bot_event(f"Bot polling failed: {e}", level="ERROR", module="telegram_poll")
    finally:
        log_local_bot_event("Bot stopped.", module="init")
