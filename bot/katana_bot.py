import telebot
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import threading
import time

from src.utils.standard_logger import get_logger

# Set up logger for this script
logger = get_logger(__name__)

# --- Heartbeat Function ---
_heartbeat_thread = None
_heartbeat_stop_event = threading.Event()

def _write_heartbeat(file_path: str):
    """Writes/updates the heartbeat file with the current timestamp."""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(datetime.now(timezone.utc).isoformat())
        # logger.debug(f"Heartbeat updated: {file_path}") # Too noisy for INFO
    except Exception as e:
        logger.error(f"Failed to write heartbeat to {file_path}: {e}", exc_info=True)

def _heartbeat_loop(file_path: str, interval: int):
    """Periodically writes a heartbeat to the specified file."""
    logger.info(f"Heartbeat thread started. Updating {file_path} every {interval} seconds.")
    while not _heartbeat_stop_event.is_set():
        _write_heartbeat(file_path)
        _heartbeat_stop_event.wait(interval) # Wait for interval or until stop_event is set
    logger.info("Heartbeat thread stopped.")

def start_heartbeat_thread():
    """Starts the global heartbeat thread if configured and not already running."""
    global _heartbeat_thread
    if _heartbeat_thread is not None and _heartbeat_thread.is_alive():
        logger.warning("Heartbeat thread already running.")
        return

    heartbeat_file = os.getenv('HEARTBEAT_FILE_PATH')
    heartbeat_interval_str = os.getenv('HEARTBEAT_INTERVAL_SECONDS', '30') # Default to 30 seconds

    if not heartbeat_file:
        logger.info("HEARTBEAT_FILE_PATH not set. Heartbeat thread will not start.")
        return

    try:
        heartbeat_interval = int(heartbeat_interval_str)
        if heartbeat_interval <= 0:
            raise ValueError("Heartbeat interval must be positive.")
    except ValueError:
        logger.error(f"Invalid HEARTBEAT_INTERVAL_SECONDS: '{heartbeat_interval_str}'. Must be a positive integer. Heartbeat disabled.", exc_info=True)
        return

    _heartbeat_stop_event.clear()
    _heartbeat_thread = threading.Thread(target=_heartbeat_loop, args=(heartbeat_file, heartbeat_interval), daemon=True)
    _heartbeat_thread.start()

def stop_heartbeat_thread():
    """Stops the global heartbeat thread."""
    global _heartbeat_thread
    if _heartbeat_thread and _heartbeat_thread.is_alive():
        logger.info("Stopping heartbeat thread...")
        _heartbeat_stop_event.set()
        _heartbeat_thread.join(timeout=5) # Wait for thread to finish
        if _heartbeat_thread.is_alive():
            logger.warning("Heartbeat thread did not stop in time.")
        _heartbeat_thread = None
    else:
        logger.info("Heartbeat thread not running or already stopped.")

# Типы сообщений в истории
MESSAGE_ROLE_USER = "user"
MESSAGE_ROLE_ASSISTANT = "assistant"

# --- Dependency Initialization ---
# Adjust imports to be cleaner and handle potential ImportErrors
try:
    from src.memory.memory_manager import MemoryManager
    from src.datafusions.datafusion import DataFusion
except ImportError:
    import sys
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from src.memory.memory_manager import MemoryManager
    from src.datafusions.datafusion import DataFusion


# Globals for dependencies, to be initialized by init_dependencies()
memory_manager: Optional[MemoryManager] = None
data_fusion: Optional[DataFusion] = None

def init_dependencies():
    """Initializes global dependencies like MemoryManager and DataFusion."""
    global memory_manager, data_fusion

    if memory_manager is None:
        logger.info("Initializing MemoryManager...")
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', '6379'))
        redis_password = os.getenv('REDIS_PASSWORD', None)
        redis_db = int(os.getenv('REDIS_DB', '0'))
        chat_ttl_str = os.getenv('REDIS_CHAT_HISTORY_TTL_SECONDS')
        chat_ttl = int(chat_ttl_str) if chat_ttl_str else None

        memory_manager = MemoryManager(
            host=redis_host, port=redis_port, db=redis_db,
            password=redis_password, chat_history_ttl_seconds=chat_ttl
        )
        logger.info("MemoryManager initialized.")
    else:
        logger.info("MemoryManager already initialized.")

    if data_fusion is None:
        logger.info("Initializing DataFusion...")
        # Assuming DataFusion is initialized without arguments for now
        data_fusion = DataFusion()
        logger.info("DataFusion initialized.")
    else:
        logger.info("DataFusion already initialized.")

def get_katana_response(history: list[dict]) -> str:
    """Gets a response from the NLP model via DataFusion."""
    logger.info(f"get_katana_response called with history: {history}")
    if data_fusion is None:
        logger.error("DataFusion is not initialized.")
        raise RuntimeError("DataFusion service not available.")

    # DataFusion is expected to handle the logic of which NLP client to use
    return data_fusion.get_response(history)


# --- Конец заглушек ---

# Получаем токен из переменной окружения
API_TOKEN = os.getenv('KATANA_TELEGRAM_TOKEN')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if API_TOKEN and ':' in API_TOKEN:
    logger.info("✅ KATANA_TELEGRAM_TOKEN loaded successfully.")
else:
    logger.error("❌ Invalid or missing Telegram API token. Please set KATANA_TELEGRAM_TOKEN env variable with format '123456:ABCDEF'.")
    raise ValueError("❌ Invalid or missing Telegram API token. Please set KATANA_TELEGRAM_TOKEN env variable with format '123456:ABCDEF'.")

if ANTHROPIC_API_KEY:
    logger.info("✅ ANTHROPIC_API_KEY loaded successfully.")
else:
    logger.warning("⚠️ ANTHROPIC_API_KEY not found. Some features might be unavailable.")

if OPENAI_API_KEY:
    logger.info("✅ OPENAI_API_KEY loaded successfully.")
else:
    logger.warning("⚠️ OPENAI_API_KEY not found. Some features might be unavailable.")

bot = telebot.TeleBot(API_TOKEN)

# Папка для сохранения команд
COMMAND_FILE_DIR = Path('commands')
COMMAND_FILE_DIR.mkdir(parents=True, exist_ok=True)

# def log_local_bot_event(message): # Эта функция больше не нужна, используем logger напрямую
#     """Логирование события бота."""
#     logger.info(message)

def handle_log_event(command_data, chat_id_str: str): # chat_id is now string
    """Обработка команды 'log_event' (заглушка)."""
    logger.info(f"handle_log_event called for chat_id {chat_id_str} with data: {command_data}")

def handle_mind_clearing(command_data, chat_id_str: str): # chat_id is now string
    """Обработка команды 'mind_clearing' (заглушка)."""
    logger.info(f"handle_mind_clearing called for chat_id {chat_id_str} with data: {command_data}")

def handle_message_impl(message):
    """
    Реализация полного цикла обработки сообщения:
    - Приём и логирование входящих сообщений.
    - Формирование контекста из MemoryManager.
    - Вызов get_katana_response с правильной историей.
    - Отправка ответа через bot.reply_to.
    - Запись в MemoryManager как входящего, так и исходящего сообщения.
    - Обработка и логирование ошибок с понятными русскими сообщениями пользователю.
    """
    chat_id_str = str(message.chat.id) # Use string chat_id for MemoryManager consistency
    user_message_text = message.text

    # 1. Логирование входящего сообщения (уже сделано в handle_message)
    # logger.info(f"Processing message from chat_id {chat_id_str}: {user_message_text}")

    # 2. Формирование контекста из MemoryManager
    # No explicit initialization like `if chat_id not in katana_states:` needed.
    # get_history will return empty list if no history.
    # For now, we retrieve full history. Later, a limit can be passed based on token constraints.
    current_history = memory_manager.get_history(chat_id_str)
    logger.info(f"Retrieved history for chat_id {chat_id_str}. Length: {len(current_history)}")


    # Попытка разобрать сообщение как JSON-команду
    is_json_command = False
    command_data = None
    try:
        parsed_json = json.loads(user_message_text)
        # Проверяем, является ли это валидной командой с нужными полями
        required_fields = {"type": str, "module": str, "args": dict, "id": (str, int)}
        is_valid_command_structure = True
        for field, expected_type in required_fields.items():
            if field not in parsed_json:
                is_valid_command_structure = False
                break
            if field == "id":
                if not any(isinstance(parsed_json[field], t) for t in expected_type):
                    is_valid_command_structure = False
                    break
            elif not isinstance(parsed_json[field], expected_type):
                is_valid_command_structure = False
                break

        if is_valid_command_structure:
            is_json_command = True
            command_data = parsed_json
        else:
            logger.info(f"Message from chat_id {chat_id_str} parsed as JSON but not a valid command structure: {user_message_text}")

    except json.JSONDecodeError:
        logger.info(f"Message from chat_id {chat_id_str} is not JSON, treating as natural language: {user_message_text}")
        pass # Не JSON, значит, обычное сообщение

    # Добавляем сообщение пользователя в историю
    memory_manager.add_message_to_history(chat_id_str, {"role": MESSAGE_ROLE_USER, "content": user_message_text})
    current_history.append({"role": MESSAGE_ROLE_USER, "content": user_message_text})

    if is_json_command and command_data:
        command_type = command_data.get("type")
        logger.info(f"Processing JSON command: type='{command_type}' for chat_id {chat_id_str}")

        if command_type == "log_event":
            handle_log_event(command_data, chat_id_str) # Corrected
            bot_response_text = "✅ 'log_event' обработан (заглушка)."
            bot.reply_to(message, bot_response_text)
            logger.info(f"Replied to chat_id {chat_id_str}: {bot_response_text}") # Corrected
            # current_history.append({"role": MESSAGE_ROLE_ASSISTANT, "content": bot_response_text}) # Replaced by memory_manager call
            memory_manager.add_message_to_history(chat_id_str, {"role": MESSAGE_ROLE_ASSISTANT, "content": bot_response_text})
            return
        elif command_type == "mind_clearing":
            handle_mind_clearing(command_data, chat_id_str) # Corrected
            # katana_states[chat_id_str] = [] # Replaced by memory_manager call
            memory_manager.clear_history(chat_id_str)
            logger.info(f"Mind clearing for chat_id {chat_id_str}. History reset.") # Corrected
            bot_response_text = "✅ Контекст диалога очищен. Начинаем с чистого листа."
            bot.reply_to(message, bot_response_text)
            logger.info(f"Replied to chat_id {chat_id_str}: {bot_response_text}") # Corrected
            # Добавляем ответ ассистента как первое сообщение после очистки
            # katana_states[chat_id_str].append({"role": MESSAGE_ROLE_ASSISTANT, "content": bot_response_text}) # Replaced
            memory_manager.add_message_to_history(chat_id_str, {"role": MESSAGE_ROLE_ASSISTANT, "content": bot_response_text})
            return
        else: # Другие JSON команды (сохранение файла)
            logger.info(f"Command type '{command_type}' not specifically handled, proceeding with default save.")
            timestamp_str = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
            command_file_name = f"{timestamp_str}_{chat_id_str}.json" # Corrected
            module_name = command_data.get('module', 'telegram_general')
            module_command_dir = COMMAND_FILE_DIR / f"telegram_mod_{module_name}" if module_name != 'telegram_general' else COMMAND_FILE_DIR / 'telegram_general'
            module_command_dir.mkdir(parents=True, exist_ok=True)
            command_file_path = module_command_dir / command_file_name

            with open(command_file_path, "w", encoding="utf-8") as f:
                json.dump(command_data, f, ensure_ascii=False, indent=2)

            bot_response_text = f"✅ Команда принята и сохранена как `{command_file_path}`."
            bot.reply_to(message, bot_response_text)
            logger.info(f"Replied to chat_id {chat_id_str}: {bot_response_text}") # Corrected
            # current_history.append({"role": MESSAGE_ROLE_ASSISTANT, "content": bot_response_text}) # Replaced
            memory_manager.add_message_to_history(chat_id_str, {"role": MESSAGE_ROLE_ASSISTANT, "content": bot_response_text})
            logger.info(f"Saved command from {chat_id_str} to {command_file_path}") # Corrected
            return
    else:
        # Это не JSON-команда или невалидная JSON-команда, значит, обычное текстовое сообщение
        # 3. Вызов get_katana_response с правильной историей
        # current_history already includes the user message due to local append after get_history
        logger.info(f"Calling get_katana_response for chat_id {chat_id_str} with history length {len(current_history)}") # Corrected

        try:
            # 3. Вызов get_katana_response с правильной историей
            katana_response_text = get_katana_response(current_history)
            logger.info(f"Katana response for chat_id {chat_id_str}: {katana_response_text}")

            # 4. Отправка ответа через bot.reply_to
            bot.reply_to(message, katana_response_text)
            logger.info(f"Replied to chat_id {chat_id_str}: {katana_response_text}")

            # 5. Запись исходящего сообщения в MemoryManager
            memory_manager.add_message_to_history(chat_id_str, {"role": MESSAGE_ROLE_ASSISTANT, "content": katana_response_text})
            logger.info(f"Appended assistant response to history for chat_id {chat_id_str}.")

        except Exception as e:
            error_id = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S_%f')
            logger.error(f"[ErrorID: {error_id}] Error during get_katana_response or reply for chat_id {chat_id_str}: {e}", exc_info=True) # Corrected
            # Формируем сообщение для пользователя
            user_error_message = (
                "😕 Произошла внутренняя ошибка при обработке вашего запроса. "
                "Команда уже уведомлена и разбирается в проблеме. "
                f"Пожалуйста, попробуйте позже. (Код ошибки: {error_id})"
            )
            bot.reply_to(message, user_error_message)
            logger.info(f"Replied to chat_id {chat_id_str} with error message: {user_error_message}") # Corrected
            # Важно: не добавляем ошибочный ответ ассистента в историю,
            # но сообщение пользователя там уже есть.


@bot.message_handler(commands=['start'])
def handle_start(message):
    """Ответ на /start"""
    chat_id_str = str(message.chat.id)
    response_text = "Привет! Я — Katana. Готов к диалогу или JSON-команде."
    bot.reply_to(message, response_text)
    logger.info(f"Replied to chat_id {chat_id_str}: {response_text}")
    logger.info(f"/start received from {chat_id_str}")

    # For /start, we might want to clear any existing short-term history
    # or simply add the welcome message. Current behavior of just adding is fine.
    # If we wanted to ensure a clean slate on /start:
    # memory_manager.clear_history(chat_id_str)

    # Add the assistant's welcome message to the history.
    memory_manager.add_message_to_history(
        chat_id_str,
        {"role": MESSAGE_ROLE_ASSISTANT, "content": response_text}
    )
    logger.info(f"Welcome message added to history for chat_id {chat_id_str} via MemoryManager.")


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Главный обработчик входящих сообщений."""
    logger.info(f"Received message from chat_id {message.chat.id} (user: {message.from_user.username}): {message.text}")
    try:
        handle_message_impl(message)
    except Exception as e:
        error_id = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S_%f')
        logger.error(f"[ErrorID: {error_id}] Unhandled exception in handle_message for chat_id {message.chat.id}: {e}", exc_info=True)
        # Уведомляем пользователя об общей ошибке, если это возможно и еще не было сделано
        try:
            user_error_message = (
                "😔 Произошла неожиданная ошибка. Мы уже занимаемся этим. "
                f"Попробуйте ваш запрос немного позже. (Код ошибки: {error_id})"
            )
            bot.reply_to(message, user_error_message)
            logger.info(f"Replied to chat_id {message.chat.id} with unhandled error message: {user_error_message}")
        except Exception as ex_reply:
            logger.error(f"[ErrorID: {error_id}] Failed to send error reply to user {message.chat.id}: {ex_reply}", exc_info=True)

if __name__ == '__main__':
    logger.info("Bot starting directly from katana_bot.py...")
    init_dependencies() # Initialize dependencies including MemoryManager
    start_heartbeat_thread()  # Start heartbeat when run directly
    try:
        # bot.polling() # Old call
        bot.polling(none_stop=True) # New call with none_stop=True
        logger.info("Bot polling started (this message might not be reached if polling is truly endless).")
        # In none_stop=True mode, polling() is a blocking call and won't complete on its own.
        # "Bot stopped." logging will only be reached if the bot process is interrupted externally (Ctrl+C, kill).
    except KeyboardInterrupt:
        logger.info("🤖 Bot polling interrupted by user (Ctrl+C) when run directly. Shutting down...")
    except Exception as e:
        logger.error(f"💥 An unexpected error occurred while running the bot directly: {e}", exc_info=True)
    finally:
        logger.info("Initiating shutdown sequence (when run directly)...")
        stop_heartbeat_thread()  # Stop heartbeat when run directly
        # Considerations for further graceful shutdown:
        # - Similar to run_bot_locally.py, true graceful handling of active message
        #   processors would require a more complex setup if using pyTelegramBotAPI's polling.
        logger.info("🛑 Katana Bot (run directly) has shut down.")