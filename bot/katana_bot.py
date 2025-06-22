import telebot
import json
import os
import logging
from pathlib import Path
from datetime import datetime, timezone

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Заглушки и глобальные переменные ---
# Это будет заменено реальной реализацией или импортом
def get_katana_response(history: list[dict]) -> str:
    """Заглушка для функции получения ответа от NLP модели."""
    logger.info(f"get_katana_response called with history: {history}")
    if not history:
        return "Катана к вашим услугам. О чём поразмыслим?"
    last_message = history[-1]['content']
    return f"Размышляю над вашим последним сообщением: '{last_message}'... (это заглушка)"

# Словарь для хранения состояний чатов (истории сообщений)
# Ключ: chat_id, Значение: list сообщений [{'role': 'user'/'assistant', 'content': 'message_text'}]
katana_states = {}

# Типы сообщений в истории
MESSAGE_ROLE_USER = "user"
MESSAGE_ROLE_ASSISTANT = "assistant"
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

def handle_log_event(command_data, chat_id):
    """Обработка команды 'log_event' (заглушка)."""
    logger.info(f"handle_log_event called for chat_id {chat_id} with data: {command_data}")

def handle_mind_clearing(command_data, chat_id):
    """Обработка команды 'mind_clearing' (заглушка)."""
    logger.info(f"handle_mind_clearing called for chat_id {chat_id} with data: {command_data}")

def handle_message_impl(message):
    """
    Реализация полного цикла обработки сообщения:
    - Приём и логирование входящих сообщений.
    - Формирование контекста из KatanaState.
    - Вызов get_katana_response с правильной историей.
    - Отправка ответа через bot.reply_to.
    - Запись в состояние как входящего, так и исходящего сообщения.
    - Обработка и логирование ошибок с понятными русскими сообщениями пользователю.
    """
    chat_id = message.chat.id
    user_message_text = message.text

    # 1. Логирование входящего сообщения (уже сделано в handle_message)
    # logger.info(f"Processing message from chat_id {chat_id}: {user_message_text}")

    # 2. Формирование контекста из KatanaState
    if chat_id not in katana_states:
        katana_states[chat_id] = []
        logger.info(f"New chat session started for chat_id {chat_id}. Initialized empty history.")

    current_history = katana_states[chat_id]

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
            logger.info(f"Message from chat_id {chat_id} parsed as JSON but not a valid command structure: {user_message_text}")

    except json.JSONDecodeError:
        logger.info(f"Message from chat_id {chat_id} is not JSON, treating as natural language: {user_message_text}")
        pass # Не JSON, значит, обычное сообщение

    # Добавляем сообщение пользователя в историю
    current_history.append({"role": MESSAGE_ROLE_USER, "content": user_message_text})

    if is_json_command and command_data:
        command_type = command_data.get("type")
        logger.info(f"Processing JSON command: type='{command_type}' for chat_id {chat_id}")

        if command_type == "log_event":
            handle_log_event(command_data, chat_id)
            bot_response_text = "✅ 'log_event' обработан (заглушка)."
            bot.reply_to(message, bot_response_text)
            logger.info(f"Replied to chat_id {chat_id}: {bot_response_text}")
            current_history.append({"role": MESSAGE_ROLE_ASSISTANT, "content": bot_response_text})
            return
        elif command_type == "mind_clearing":
            handle_mind_clearing(command_data, chat_id)
            katana_states[chat_id] = [] # Очищаем историю
            logger.info(f"Mind clearing for chat_id {chat_id}. History reset.")
            bot_response_text = "✅ Контекст диалога очищен. Начинаем с чистого листа."
            bot.reply_to(message, bot_response_text)
            logger.info(f"Replied to chat_id {chat_id}: {bot_response_text}")
            # Добавляем ответ ассистента как первое сообщение после очистки
            katana_states[chat_id].append({"role": MESSAGE_ROLE_ASSISTANT, "content": bot_response_text})
            return
        else: # Другие JSON команды (сохранение файла)
            logger.info(f"Command type '{command_type}' not specifically handled, proceeding with default save.")
            timestamp_str = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
            command_file_name = f"{timestamp_str}_{chat_id}.json"
            module_name = command_data.get('module', 'telegram_general')
            module_command_dir = COMMAND_FILE_DIR / f"telegram_mod_{module_name}" if module_name != 'telegram_general' else COMMAND_FILE_DIR / 'telegram_general'
            module_command_dir.mkdir(parents=True, exist_ok=True)
            command_file_path = module_command_dir / command_file_name

            with open(command_file_path, "w", encoding="utf-8") as f:
                json.dump(command_data, f, ensure_ascii=False, indent=2)

            bot_response_text = f"✅ Команда принята и сохранена как `{command_file_path}`."
            bot.reply_to(message, bot_response_text)
            logger.info(f"Replied to chat_id {chat_id}: {bot_response_text}")
            current_history.append({"role": MESSAGE_ROLE_ASSISTANT, "content": bot_response_text})
            logger.info(f"Saved command from {chat_id} to {command_file_path}")
            return
    else:
        # Это не JSON-команда или невалидная JSON-команда, значит, обычное текстовое сообщение
        # 3. Вызов get_katana_response с правильной историей
        logger.info(f"Calling get_katana_response for chat_id {chat_id} with history length {len(current_history)}")

        try:
            # 3. Вызов get_katana_response с правильной историей
            katana_response_text = get_katana_response(current_history)
            logger.info(f"Katana response for chat_id {chat_id}: {katana_response_text}")

            # 4. Отправка ответа через bot.reply_to
            bot.reply_to(message, katana_response_text)
            logger.info(f"Replied to chat_id {chat_id}: {katana_response_text}")

            # 5. Запись исходящего сообщения в состояние
            current_history.append({"role": MESSAGE_ROLE_ASSISTANT, "content": katana_response_text})
            logger.info(f"Appended assistant response to history for chat_id {chat_id}. History length: {len(current_history)}")

        except Exception as e:
            error_id = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S_%f')
            logger.error(f"[ErrorID: {error_id}] Error during get_katana_response or reply for chat_id {chat_id}: {e}", exc_info=True)
            # Формируем сообщение для пользователя
            user_error_message = (
                "😕 Произошла внутренняя ошибка при обработке вашего запроса. "
                "Команда уже уведомлена и разбирается в проблеме. "
                f"Пожалуйста, попробуйте позже. (Код ошибки: {error_id})"
            )
            bot.reply_to(message, user_error_message)
            logger.info(f"Replied to chat_id {chat_id} with error message: {user_error_message}")
            # Важно: не добавляем ошибочный ответ ассистента в историю,
            # но сообщение пользователя там уже есть.


@bot.message_handler(commands=['start'])
def handle_start(message):
    """Ответ на /start"""
    response_text = "Привет! Я — Katana. Готов к диалогу или JSON-команде."
    bot.reply_to(message, response_text)
    logger.info(f"Replied to chat_id {message.chat.id}: {response_text}")
    logger.info(f"/start received from {message.chat.id}")
    # Инициализируем состояние для нового пользователя при /start
    if message.chat.id not in katana_states:
        katana_states[message.chat.id] = []
    katana_states[message.chat.id].append({"role": MESSAGE_ROLE_ASSISTANT, "content": "Привет! Я — Katana. Готов к диалогу или JSON-команде."})


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
    logger.info("Bot starting...")
    # bot.polling() # Old call
    bot.polling(none_stop=True) # New call with none_stop=True
    logger.info("Bot polling started (this message might not be reached if polling is truly endless).")
    # В режиме none_stop=True, poling() является блокирующим вызовом и не завершится сам по себе.
    # Логирование "Bot stopped." будет достигнуто только если процесс бота будет прерван извне (Ctrl+C, kill).
    # Для run_bot_locally.py это нормально, т.к. мы ожидаем, что бот будет работать до прерывания.