"""
Katana Telegram Bot
-------------------
This script implements a Telegram bot named Katana. The bot listens for incoming
messages, expecting them to be JSON-formatted commands. It validates these commands
and routes them to appropriate handlers.

Core functionalities:
- Receives messages and parses them as JSON.
- Validates JSON commands against a required structure (type, module, args, id).
- Handles a '/start' command.
- Saves unhandled valid commands to a file system, organized by module.
- Integrates with an AIClient to process 'ai_query' commands, allowing users
  to interact with various AI models (currently mocked).

Command Structure:
The bot expects JSON objects with the following fields:
  "type" (str): The type of command (e.g., "log_event", "mind_clearing", "ai_query").
  "module" (str): The conceptual module this command pertains to.
  "args" (dict): A dictionary of arguments specific to the command type.
  "id" (str or int): A unique identifier for the command instance.

For 'ai_query' commands, 'args' should include:
  "prompt" (str): The text prompt for the AI.
  "provider" (str, optional): The AI provider (e.g., "openai", "anthropic"). Defaults to "openai".
  Other provider-specific parameters (e.g., "model") can also be included in 'args'.

Environment Variables:
- KATANA_TELEGRAM_TOKEN: The API token for the Telegram bot.

Directory Structure for Saved Commands:
- commands/telegram_general/
- commands/telegram_mod_<module_name>/

The AIClient component uses 'ai_keys.json' (by default in the project root)
for managing API keys for different AI providers. See 'ai_keys.json.example'.
"""
import telebot
import json
import os
from pathlib import Path
from datetime import datetime

# Assuming ai_client is in a subfolder 'ai_client' relative to this file's location
# and that katana_bot.py is run from the project root.
# So, 'ai_keys.json' is expected in the project root.
try:
    from .ai_client.ai_client import AIClient
    from .ai_client.key_manager import DEFAULT_KEYS_FILE # To reference where keys are expected
except ImportError:
    # Fallback for scenarios where the script might be run directly and '.' imports fail
    # This might happen if 'bot' is not treated as a package.
    from ai_client.ai_client import AIClient
    from ai_client.key_manager import DEFAULT_KEYS_FILE


# Получаем токен из переменной окружения
API_TOKEN = os.getenv('KATANA_TELEGRAM_TOKEN', 'YOUR_API_TOKEN')
if not API_TOKEN or ':' not in API_TOKEN:
    raise ValueError("❌ Invalid or missing Telegram API token. Please set KATANA_TELEGRAM_TOKEN env variable with format '123456:ABCDEF'.")

bot = telebot.TeleBot(API_TOKEN)

# AI Client Initialization
# Assumes katana_bot.py is in 'bot/' and ai_keys.json is in the project root.
# If katana_bot.py is run from project root: python bot/katana_bot.py or python -m bot.katana_bot
# then Path("ai_keys.json") correctly points to project_root/ai_keys.json
# If katana_bot.py is run from bot/: cd bot; python katana_bot.py
# then Path("../ai_keys.json") would be needed.
# The current DEFAULT_KEYS_FILE in key_manager.py is "ai_keys.json"
# KeyManager will resolve this relative to its CWD when it runs.
# If katana_bot.py is the entry point and is in project_root/bot/,
# and it instantiates AIClient which instantiates KeyManager,
# Python's CWD is usually the directory from which the script was launched.
# So, if launched from project_root, key_manager will look for ai_keys.json in project_root.
ai_client_keys_path = DEFAULT_KEYS_FILE # This is "ai_keys.json"
ai_client = AIClient(keys_filepath=ai_client_keys_path)
print(f"AIClient initialized. Expecting API keys in: {os.path.abspath(ai_client_keys_path)}")


# Папка для сохранения команд
# If run from project root, this will be project_root/commands
# If run from bot/, this will be bot/commands
COMMAND_FILE_DIR = Path('commands')
COMMAND_FILE_DIR.mkdir(parents=True, exist_ok=True)

def log_local_bot_event(message):
    """Вывод лога события в консоль."""
    # Using print for now, consider proper logging integration later
    print(f"[BOT EVENT] {datetime.utcnow().isoformat()}: {message}")

def handle_log_event(command_data, chat_id):
    """Обработка команды 'log_event' (заглушка)."""
    log_local_bot_event(f"handle_log_event called for chat_id {chat_id} with data: {command_data}")

def handle_mind_clearing(command_data, chat_id):
    """Обработка команды 'mind_clearing' (заглушка)."""
    log_local_bot_event(f"handle_mind_clearing called for chat_id {chat_id} with data: {command_data}")

def handle_ai_query(command_data, chat_id, message_obj):
    """
    Обработка команды 'ai_query'.

    This handler processes AI query requests. It expects 'prompt' and optionally 'provider'
    within the 'args' dictionary of the command_data.

    Example 'ai_query' command structure in args:
    "args": {
        "prompt": "Tell me about large language models.",
        "provider": "openai", // Optional, defaults to "openai"
        "model": "gpt-3.5-turbo" // Optional, provider-specific
    }
    """
    log_local_bot_event(f"handle_ai_query called for chat_id {chat_id} with data: {command_data}")

    args = command_data.get("args", {})
    prompt = args.get("prompt")
    provider = args.get("provider", "openai") # Default to openai if not specified
    # Allow other AI client args to be passed through, e.g. "model"
    additional_params = {k: v for k, v in args.items() if k not in ["prompt", "provider"]}

    if not prompt:
        bot.reply_to(message_obj, "❌ Error: 'prompt' is missing in 'args' for 'ai_query'.")
        log_local_bot_event(f"Missing prompt for ai_query from {chat_id}.")
        return

    bot.reply_to(message_obj, f"⏳ Processing your AI query with {provider}...")
    log_local_bot_event(f"Sending prompt to AI client: Provider: {provider}, Prompt: '{prompt[:50]}...'")

    try:
        response = ai_client.generate_text(prompt=prompt, provider=provider, **additional_params)
        bot.reply_to(message_obj, f"🤖 AI Response:\n{response}")
        log_local_bot_event(f"Successfully received AI response for {chat_id}.")
    except Exception as e:
        bot.reply_to(message_obj, f"❌ Error processing your AI query: {e}")
        log_local_bot_event(f"Error during AI query for {chat_id}: {e}")


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

    try:
        command_data = json.loads(command_text)
    except json.JSONDecodeError:
        bot.reply_to(message, "❌ Error: Invalid JSON format.")
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
    elif command_type == "ai_query":
        handle_ai_query(command_data, chat_id, message) # Pass the full message object
        # handle_ai_query will send its own replies
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