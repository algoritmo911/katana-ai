import telebot
from telebot.async_telebot import AsyncTeleBot
import json
import os
from pathlib import Path
from datetime import datetime
from bot.chat_history import ChatHistory

# Получаем токен из переменной окружения
API_TOKEN = os.getenv('KATANA_TELEGRAM_TOKEN', 'YOUR_API_TOKEN')
if not API_TOKEN or ':' not in API_TOKEN:
    raise ValueError("❌ Invalid or missing Telegram API token. Please set KATANA_TELEGRAM_TOKEN env variable with format '123456:ABCDEF'.")

bot = AsyncTeleBot(API_TOKEN)

# Папка для сохранения команд
COMMAND_FILE_DIR = Path('commands')
COMMAND_FILE_DIR.mkdir(parents=True, exist_ok=True)

def log_local_bot_event(message):
    """Вывод лога события в консоль."""
    print(f"[BOT EVENT] {datetime.utcnow().isoformat()}: {message}")

def handle_log_event(command_data, chat_id):
    """Обработка команды 'log_event' (заглушка)."""
    log_local_bot_event(f"handle_log_event called for chat_id {chat_id} with data: {command_data}")

async def handle_mind_clearing(command_data, chat_id):
    """Обработка команды 'mind_clearing' (заглушка)."""
    log_local_bot_event(f"handle_mind_clearing called for chat_id {chat_id} with data: {command_data}")

@bot.message_handler(commands=['start'])
async def handle_start(message):
    """Ответ на /start"""
    await bot.reply_to(message, "Привет! Я — Katana. Отправь JSON-команду, чтобы начать.")
    log_local_bot_event(f"/start received from {message.chat.id}")
    history = ChatHistory(message.chat.id)
    history.add_message("user", "/start", message.date)
    history.add_message("bot", "Привет! Я — Katana. Отправь JSON-команду, чтобы начать.", datetime.utcnow().isoformat())

@bot.message_handler(commands=['clear_history'])
async def handle_clear_history(message):
    """Очистка истории чата."""
    chat_id = message.chat.id
    history = ChatHistory(chat_id)
    history.clear_history()
    await bot.reply_to(message, "История чата очищена.")
    log_local_bot_event(f"Chat history cleared for {chat_id}")

@bot.message_handler(func=lambda message: True)
async def handle_message(message):
    """Главный обработчик входящих сообщений."""
    chat_id = message.chat.id
    command_text = message.text

    log_local_bot_event(f"Received message from {chat_id}: {command_text}")

    # Сохраняем сообщение в историю
    history = ChatHistory(chat_id)
    history.add_message("user", command_text, message.date)


    try:
        command_data = json.loads(command_text)
    except json.JSONDecodeError:
        await bot.reply_to(message, "❌ Error: Invalid JSON format.")
        log_local_bot_event(f"Invalid JSON from {chat_id}: {command_text}")
        history.add_message("bot", "❌ Error: Invalid JSON format.", datetime.utcnow().isoformat())
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
            await bot.reply_to(message, error_msg)
            log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text})")
            history.add_message("bot", error_msg, datetime.utcnow().isoformat())
            return
        if field == "id":
            if not any(isinstance(command_data[field], t) for t in expected_type):
                error_msg = f"❌ Error: Field '{field}' must be type str or int. Got {type(command_data[field]).__name__}."
                await bot.reply_to(message, error_msg)
                log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text})")
                history.add_message("bot", error_msg, datetime.utcnow().isoformat())
                return
        elif not isinstance(command_data[field], expected_type):
            error_msg = f"❌ Error: Field '{field}' must be type {expected_type.__name__}. Got {type(command_data[field]).__name__}."
            await bot.reply_to(message, error_msg)
            log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text})")
            history.add_message("bot", error_msg, datetime.utcnow().isoformat())
            return

    command_type = command_data.get("type")
    response_message = ""

    if command_type == "log_event":
        handle_log_event(command_data, chat_id) # Предполагается, что эта функция остается синхронной или будет обновлена
        response_message = "✅ 'log_event' processed (placeholder)."
        await bot.reply_to(message, response_message)
        history.add_message("bot", response_message, datetime.utcnow().isoformat())
        return
    elif command_type == "mind_clearing":
        await handle_mind_clearing(command_data, chat_id) # Обновлено для await
        response_message = "✅ 'mind_clearing' processed (placeholder)."
        await bot.reply_to(message, response_message)
        history.add_message("bot", response_message, datetime.utcnow().isoformat())
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
    
    response_message = f"✅ Command received and saved as `{command_file_path}`."
    await bot.reply_to(message, response_message)
    history.add_message("bot", response_message, datetime.utcnow().isoformat())
    log_local_bot_event(f"Saved command from {chat_id} to {command_file_path}")

if __name__ == '__main__':
    import asyncio
    log_local_bot_event("Bot starting...")
    asyncio.run(bot.polling())
    log_local_bot_event("Bot stopped.")