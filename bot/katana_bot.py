import telebot
import json
import os
from pathlib import Path
from datetime import datetime
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Получаем токен из переменной окружения
API_TOKEN = os.getenv('KATANA_TELEGRAM_TOKEN')
# Определяем тестовый режим, например, через другую переменную окружения
IS_TEST_ENVIRONMENT = os.getenv('ENV_TYPE', 'prod').lower() == 'test'

bot = None

if API_TOKEN and ':' in API_TOKEN:
    logging.info("✅ Telegram token loaded successfully from KATANA_TELEGRAM_TOKEN.")
    try:
        bot = telebot.TeleBot(API_TOKEN)
        logging.info("✅ TeleBot instance initialized successfully.")
    except Exception as e:
        logging.error(f"❌ Failed to initialize TeleBot: {e}")
        if IS_TEST_ENVIRONMENT:
            logging.warning("🧪 Test environment detected. Proceeding without a functional bot instance due to initialization error.")
            # In a real test scenario with a mock Telebot server, we might assign a mock object here.
            # For now, 'bot' will remain None, and parts of the app might not function.
            pass # bot remains None
        else:
            raise  # Re-raise the exception if not in test environment
else:
    error_message = "❌ Invalid or missing Telegram API token. Please set KATANA_TELEGRAM_TOKEN env variable with format '123456:ABCDEF'."
    logging.error(error_message)
    if IS_TEST_ENVIRONMENT:
        logging.warning("🧪 Test environment detected. KATANA_TELEGRAM_TOKEN is missing or invalid. Proceeding without a functional bot instance.")
        # bot remains None, or assign a mock if available/useful
    else:
        # For a production environment, this is a critical failure.
        # Depending on desired behavior, could exit or raise. Raising ValueError is appropriate.
        raise ValueError(error_message)

# Fallback for bot instance if it's None (e.g. in test environment with no token)
# This is a basic fallback. Operations requiring 'bot' will fail if it's None.
# A more robust solution in a test environment would be a full mock of the TeleBot API.
if bot is None and IS_TEST_ENVIRONMENT:
    logging.warning("🧪 Bot instance is None in test environment. Some functionalities will be unavailable.")
    # Potentially, assign a dummy/mock bot object here if needed for tests to pass without a real bot.
    # For example:
    # class MockBot:
    #     def reply_to(self, message, text): logging.info(f"MockBot.reply_to: {text}")
    #     # Add other methods that are called on the bot object
    # if IS_TEST_ENVIRONMENT: bot = MockBot()


# Папка для сохранения команд
COMMAND_FILE_DIR = Path('commands')
COMMAND_FILE_DIR.mkdir(parents=True, exist_ok=True)

# def log_local_bot_event(message): # Replaced by standard logging
#     """Вывод лога события в консоль."""
#     print(f"[BOT EVENT] {datetime.utcnow().isoformat()}: {message}")

def handle_log_event(command_data, chat_id):
    """Обработка команды 'log_event' (заглушка)."""
    logging.info(f"handle_log_event called for chat_id {chat_id} with data: {command_data}")

def handle_mind_clearing(command_data, chat_id):
    """Обработка команды 'mind_clearing' (заглушка)."""
    logging.info(f"handle_mind_clearing called for chat_id {chat_id} with data: {command_data}")

@bot.message_handler(commands=['start'])
def handle_start(message):
    """Ответ на /start"""
    if not bot:
        logging.error("handle_start: Bot not initialized.")
        return
    bot.reply_to(message, "Привет! Я — Katana. Отправь JSON-команду, чтобы начать.")
    logging.info(f"/start received from {message.chat.id}")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Главный обработчик входящих сообщений."""
    if not bot:
        logging.error("handle_message: Bot not initialized.")
        # Optionally, you could try to send a message via another channel if the bot is down,
        # but for now, just log and return.
        return

    chat_id = message.chat.id
    command_text = message.text

    # Log entire message object for more detailed debugging if needed, converting to dict first
    try:
        message_dict = message.__dict__ if hasattr(message, '__dict__') else str(message)
        logging.info(f"Received message update from chat_id {chat_id}. Full message object: {message_dict}")
    except Exception as e:
        logging.warning(f"Could not serialize full message object for logging: {e}")
        logging.info(f"Received message from chat_id {chat_id} with text: {command_text}")


    try:
        command_data = json.loads(command_text)
        logging.info(f"Successfully parsed JSON for chat_id {chat_id}: {command_data}")
    except json.JSONDecodeError as e:
        user_error_msg = f"❌ Ошибка: Некорректный формат JSON. Пожалуйста, проверьте синтаксис.\nДетали: {e}"
        bot.reply_to(message, user_error_msg)
        logging.error(f"Invalid JSON from chat_id {chat_id}. Text: '{command_text}'. Error: {e}")
        return

    required_fields = {
        "type": str,
        "module": str,
        "args": dict,
        "id": (str, int)  # Allows id to be string or integer
    }

    validation_errors = []
    for field, expected_type_or_tuple in required_fields.items():
        if field not in command_data:
            validation_errors.append(f"Отсутствует обязательное поле '{field}'.")
        else:
            # Handle cases where expected_type_or_tuple is a single type or a tuple of types
            if isinstance(expected_type_or_tuple, tuple):
                # Expecting one of several types (e.g., str or int for 'id')
                if not any(isinstance(command_data[field], t) for t in expected_type_or_tuple):
                    expected_type_names = ", ".join([t.__name__ for t in expected_type_or_tuple])
                    validation_errors.append(
                        f"Поле '{field}' должно быть одного из типов: {expected_type_names}. Получено: {type(command_data[field]).__name__}."
                    )
            elif not isinstance(command_data[field], expected_type_or_tuple):
                # Expecting a single specific type
                validation_errors.append(
                    f"Поле '{field}' должно быть типа {expected_type_or_tuple.__name__}. Получено: {type(command_data[field]).__name__}."
                )

    if validation_errors:
        user_error_msg = "❌ Ошибка валидации команды:\n" + "\n".join(validation_errors)
        bot.reply_to(message, user_error_msg)
        logging.error(f"Command validation failed for chat_id {chat_id}. Errors: {'; '.join(validation_errors)}. Command: {command_text}")
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

    log_local_bot_event(f"Command type '{command_type}' not specifically handled, proceeding with default save.")

    timestamp_str = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
    command_file_name = f"{timestamp_str}_{chat_id}.json"
    
    module_name = command_data.get('module', 'telegram_general')
    module_command_dir = COMMAND_FILE_DIR / f"telegram_mod_{module_name}" if module_name != 'telegram_general' else COMMAND_FILE_DIR / 'telegram_general'
    module_command_dir.mkdir(parents=True, exist_ok=True)
    command_file_path = module_command_dir / command_file_name

    try:
        with open(command_file_path, "w", encoding="utf-8") as f:
            json.dump(command_data, f, ensure_ascii=False, indent=2)

        bot.reply_to(message, f"✅ Команда получена и сохранена как `{command_file_path}`.")
        logging.info(f"Saved command from {chat_id} to {command_file_path}")
    except IOError as e:
        bot.reply_to(message, "❌ Ошибка: Не удалось сохранить команду на сервере.")
        logging.error(f"Failed to save command from {chat_id} to {command_file_path}. Error: {e}")

if __name__ == '__main__':
    logging.info("Bot starting...")
    if bot:
        try:
            logging.info("Starting bot polling...")
            bot.polling(none_stop=True) # none_stop=True to keep polling even on minor errors
        except Exception as e:
            logging.error(f"❌ Bot polling failed critically: {e}")
        finally:
            logging.info("Bot polling has stopped.")
    else:
        logging.error("Bot instance not initialized. Cannot start polling.")