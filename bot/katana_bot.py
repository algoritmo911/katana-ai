import telebot
import json
import os
from pathlib import Path
from datetime import datetime
import logging # Импортируем стандартный logging

# Импортируем NLPService
from nlp_service import NLPService, NLPProviderConfig # Добавлено NLPProviderConfig для возможной детальной настройки если потребуется

# Настройка логирования для бота, чтобы соответствовать nlp_service
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Получаем токен из переменной окружения
API_TOKEN = os.getenv('KATANA_TELEGRAM_TOKEN', 'YOUR_API_TOKEN')
if not API_TOKEN or ':' not in API_TOKEN:
    logger.error("❌ Invalid or missing Telegram API token. Please set KATANA_TELEGRAM_TOKEN env variable with format '123456:ABCDEF'.")
    raise ValueError("❌ Invalid or missing Telegram API token. Please set KATANA_TELEGRAM_TOKEN env variable with format '123456:ABCDEF'.")

bot = telebot.TeleBot(API_TOKEN)
nlp_service_instance = NLPService() # Инициализация NLPService

# Папка для сохранения команд
COMMAND_FILE_DIR = Path('commands')
COMMAND_FILE_DIR.mkdir(parents=True, exist_ok=True)

# Заменяем print на logger для консистентности
def log_local_bot_event(message_text):
    """Вывод лога события с использованием logging."""
    logger.info(f"[BOT EVENT] {message_text}")

def handle_log_event(command_data, chat_id):
    """Обработка команды 'log_event' (заглушка)."""
    log_local_bot_event(f"handle_log_event called for chat_id {chat_id} with data: {command_data}")

def handle_mind_clearing(command_data, chat_id):
    """Обработка команды 'mind_clearing' (заглушка)."""
    log_local_bot_event(f"handle_mind_clearing called for chat_id {chat_id} with data: {command_data}")

@bot.message_handler(commands=['start'])
def handle_start(message):
    """Ответ на /start"""
    bot.reply_to(message, "Привет! Я — Katana. Отправь JSON-команду, чтобы начать. Доступна команда 'nlp_request'.")
    log_local_bot_event(f"/start received from {message.chat.id}")

@bot.message_handler(content_types=['text']) # Явно указываем, что обрабатываем только текстовые сообщения
def handle_message(message):
    """Главный обработчик входящих сообщений."""
    chat_id = message.chat.id
    command_text = message.text

    log_local_bot_event(f"Received message from {chat_id}: {command_text}")

    try:
        command_data = json.loads(command_text)
    except json.JSONDecodeError:
        bot.reply_to(message, "❌ Error: Invalid JSON format.")
        log_local_bot_event(f"Invalid JSON from {chat_id}: {command_text}")
        return

    # Обновленные обязательные поля для стандартных команд
    # Для nlp_request будет своя валидация
    standard_required_fields = {
        "type": str,
        "module": str,
        "args": dict,
        "id": (str, int)
    }

    command_type = command_data.get("type")

    # Обработка новой команды nlp_request
    if command_type == "nlp_request":
        nlp_args = command_data.get("args", {})
        text_to_process = nlp_args.get("text")
        image_url = nlp_args.get("image_url")
        audio_url = nlp_args.get("audio_url")
        provider_name = nlp_args.get("provider")
        context_data = nlp_args.get("context") # Переименовано из context_dialog для ясности
        task_type = nlp_args.get("task_type", "general")
        session_id = nlp_args.get("session_id", str(chat_id)) # Используем chat_id как session_id по умолчанию

        # Валидация: хотя бы один из text, image_url, audio_url должен присутствовать
        if not text_to_process and not image_url and not audio_url:
            bot.reply_to(message, "❌ Error for 'nlp_request': At least one of 'text', 'image_url', or 'audio_url' must be provided in 'args'.")
            log_local_bot_event(f"Invalid 'nlp_request' from {chat_id}: missing text, image_url, and audio_url.")
            return

        # Валидация типов, если они предоставлены
        if text_to_process is not None and not isinstance(text_to_process, str):
            bot.reply_to(message, "❌ Error for 'nlp_request': 'text' must be a string if provided.")
            log_local_bot_event(f"Invalid 'nlp_request' from {chat_id}: 'text' is not a string.")
            return
        if image_url is not None and not isinstance(image_url, str): # TODO: Добавить валидацию URL
            bot.reply_to(message, "❌ Error for 'nlp_request': 'image_url' must be a string (URL) if provided.")
            log_local_bot_event(f"Invalid 'nlp_request' from {chat_id}: 'image_url' is not a string.")
            return
        if audio_url is not None and not isinstance(audio_url, str): # TODO: Добавить валидацию URL
            bot.reply_to(message, "❌ Error for 'nlp_request': 'audio_url' must be a string (URL) if provided.")
            log_local_bot_event(f"Invalid 'nlp_request' from {chat_id}: 'audio_url' is not a string.")
            return

        log_local_bot_event(
            f"Processing 'nlp_request' for chat_id {chat_id} with "
            f"text: '{text_to_process}', image_url: '{image_url}', audio_url: '{audio_url}', "
            f"provider: {provider_name or 'default'}, task_type: {task_type}"
        )

        try:
            if image_url or audio_url: # Если есть мультимедийные данные, используем process_multimodal
                nlp_response = nlp_service_instance.process_multimodal(
                    text=text_to_process,
                    image_url=image_url,
                    audio_url=audio_url,
                    provider_name=provider_name,
                    context=context_data,
                    task_type=task_type,
                    session_id=session_id
                )
            else: # Иначе, это чисто текстовый запрос (text_to_process здесь не None из-за первой проверки)
                nlp_response = nlp_service_instance.process_text(
                    text=text_to_process,
                    provider_name=provider_name,
                    context=context_data,
                    task_type=task_type,
                    session_id=session_id
                )

            response_str = json.dumps(nlp_response, indent=2, ensure_ascii=False)
            bot.reply_to(message, f"✅ NLP Response:\n```json\n{response_str}\n```")
            log_local_bot_event(f"Successfully processed 'nlp_request' for {chat_id}. Response: {nlp_response}")
        except Exception as e:
            bot.reply_to(message, f"❌ Error processing 'nlp_request': {str(e)}")
            logger.exception(f"Error during 'nlp_request' for {chat_id}:") # Используем logger.exception для стектрейса
        return

    # Валидация для стандартных команд (не nlp_request)
    # Сначала проверяем наличие 'type', чтобы дать осмысленную ошибку, если его нет
    if "type" not in command_data or not isinstance(command_data["type"], str):
        bot.reply_to(message, "❌ Error: Missing or invalid 'type' field in JSON command.")
        log_local_bot_event(f"Validation failed for {chat_id}: Missing or invalid 'type'. (Command: {command_text})")
        return

    for field, expected_type in standard_required_fields.items():
        if field not in command_data:
            error_msg = f"❌ Error: Missing required field '{field}' for command type '{command_type}'."
            bot.reply_to(message, error_msg)
            log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text})")
            return
        current_value = command_data[field]
        if field == "id": # Специальная проверка для id (str или int)
            if not any(isinstance(current_value, t) for t in expected_type): # type: ignore
                error_msg = f"❌ Error: Field '{field}' must be type str or int. Got {type(current_value).__name__}."
                bot.reply_to(message, error_msg)
                log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text})")
                return
        elif not isinstance(current_value, expected_type): # Общая проверка типа
            expected_type_name = expected_type.__name__ if not isinstance(expected_type, tuple) else " or ".join(t.__name__ for t in expected_type) # type: ignore
            error_msg = f"❌ Error: Field '{field}' must be type {expected_type_name}. Got {type(current_value).__name__}."
            bot.reply_to(message, error_msg)
            log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text})")
            return

    # Обработка существующих команд
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

    with open(command_file_path, "w", encoding="utf-8") as f:
        json.dump(command_data, f, ensure_ascii=False, indent=2)
    
    bot.reply_to(message, f"✅ Command received and saved as `{command_file_path}`.")
    log_local_bot_event(f"Saved command from {chat_id} to {command_file_path}")

if __name__ == '__main__':
    log_local_bot_event("Bot starting...")
    bot.polling()
    log_local_bot_event("Bot stopped.")