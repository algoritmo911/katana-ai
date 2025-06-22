import telebot.async_telebot as async_telebot # Use async version
import json
import os
import asyncio # Required for async operations
from pathlib import Path
from datetime import datetime

# Получаем токен из переменной окружения
API_TOKEN = os.getenv('KATANA_TELEGRAM_TOKEN', 'YOUR_API_TOKEN')
if not API_TOKEN or ':' not in API_TOKEN:
    raise ValueError("❌ Invalid or missing Telegram API token. Please set KATANA_TELEGRAM_TOKEN env variable with format '123456:ABCDEF'.")

bot = async_telebot.AsyncTeleBot(API_TOKEN) # Use AsyncTeleBot

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

@bot.message_handler(commands=['start'])
async def handle_start(message): # Make async
    """Ответ на /start"""
    await bot.reply_to(message, "Привет! Я — Katana. Отправь JSON-команду, чтобы начать.") # Add await
    log_local_bot_event(f"/start received from {message.chat.id}")

@bot.message_handler(func=lambda message: True)
async def handle_message(message): # Make async
    """Главный обработчик входящих сообщений."""
    chat_id = message.chat.id
    command_text = message.text

    log_local_bot_event(f"Received message from {chat_id}: {command_text}")

    try:
        command_data = json.loads(command_text)
    except json.JSONDecodeError:
        await bot.reply_to(message, "❌ Error: Invalid JSON format.") # Add await
        log_local_bot_event(f"Invalid JSON from {chat_id}: {command_text}")
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
            log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text})")
            return
        if field == "id":
            if not any(isinstance(command_data[field], t) for t in expected_type):
                error_msg = f"❌ Error: Field '{field}' must be type str or int. Got {type(command_data[field]).__name__}."
                bot.reply_to(message, error_msg)
                log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text})")
                return
        elif not isinstance(command_data[field], expected_type):
            error_msg = f"❌ Error: Field '{field}' must be type {expected_type.__name__}. Got {type(command_data[field]).__name__}."
            bot.reply_to(message, error_msg)
            log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text})")
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

    with open(command_file_path, "w", encoding="utf-8") as f:
        json.dump(command_data, f, ensure_ascii=False, indent=2)
    
    bot.reply_to(message, f"✅ Command received and saved as `{command_file_path}`.")
    log_local_bot_event(f"Saved command from {chat_id} to {command_file_path}")

# Placeholder for AI request handler
async def handle_ai_request(command_data, chat_id, message):
    """Handles AI requests by routing to the appropriate provider."""
    log_local_bot_event(f"handle_ai_request called for chat_id {chat_id} with data: {command_data}")

    ai_provider = command_data.get("args", {}).get("provider")
    prompt = command_data.get("args", {}).get("prompt")
    model = command_data.get("args", {}).get("model")
    # Make sure message object is available for replies
    # message_to_reply = message # if message is passed directly, otherwise ensure it's part of command_data or context

    if not ai_provider or not prompt:
        await bot.reply_to(message, "❌ Error: 'provider' and 'prompt' are required in 'args' for AI requests.") # Add await
        return

    response_text = None
    if ai_provider == "openai":
        from bot.ai_providers.openai import generate_text_openai
        # Ensure model is provided or use a default
        response_text = await generate_text_openai(prompt, model=model if model else "gpt-3.5-turbo")
    elif ai_provider == "anthropic":
        from bot.ai_providers.anthropic import generate_text_anthropic
        # Ensure model is provided or use a default
        response_text = await generate_text_anthropic(prompt, model=model if model else "claude-2")
    elif ai_provider == "huggingface":
        from bot.ai_providers.huggingface import generate_text_huggingface
        # Ensure model is provided or use a default for text generation
        # Add more specific handling if other HuggingFace tasks like text-to-image are needed
        if command_data.get("args", {}).get("task") == "text-to-image":
            from bot.ai_providers.huggingface import text_to_image_huggingface
            image_bytes = await text_to_image_huggingface(prompt, model=model if model else "stabilityai/stable-diffusion-2")
            if image_bytes:
                await bot.send_photo(chat_id, photo=image_bytes, caption=f"Generated image for: {prompt}") # Add await
            else:
                await bot.reply_to(message, "❌ Error generating image with HuggingFace.") # Add await
            return # Exit after sending image or error
        else: # Default to text generation
            response_text = await generate_text_huggingface(prompt, model=model if model else "gpt2")
    else:
        await bot.reply_to(message, f"❌ Error: Unknown AI provider '{ai_provider}'. Supported: openai, anthropic, huggingface.") # Add await
        return

    if response_text:
        await bot.reply_to(message, f"🤖 AI Response ({ai_provider}):\n{response_text}") # Add await
    else:
        await bot.reply_to(message, f"❌ Error: Could not get a response from {ai_provider}.") # Add await


# The duplicated handle_message function and its related comments are removed.
# The correct async def handle_message is already defined above and decorated.

async def main(): # Create an async main function
    log_local_bot_event("Bot starting...")
    await bot.polling() # Use await for polling
    log_local_bot_event("Bot stopped.")

if __name__ == '__main__':
    asyncio.run(main()) # Run the async main function