import telebot
import json
import os
import asyncio # Added for async NLP calls
import gzip # For compressing command files
import shutil # For cleanup tasks (potentially)
from pathlib import Path
from datetime import datetime, timedelta # For cleanup logic

from nlp_service import NLPService # Import NLPService
from tts_service import TTSService # Import TTSService

# Получаем токен из переменной окружения
API_TOKEN = os.getenv('KATANA_TELEGRAM_TOKEN', 'YOUR_API_TOKEN')
if not API_TOKEN or ':' not in API_TOKEN:
    raise ValueError("❌ Invalid or missing Telegram API token. Please set KATANA_TELEGRAM_TOKEN env variable with format '123456:ABCDEF'.")

bot = telebot.TeleBot(API_TOKEN, parse_mode=None) # parse_mode=None for default, or 'HTML', 'Markdown'
nlp_service = NLPService() # Instantiate NLPService
tts_service = TTSService() # Instantiate TTSService

# In-memory store for user voice preferences {chat_id: lang_code}
user_voice_preferences = {}
# Example: user_voice_preferences = {12345: 'es', 67890: 'fr'}

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
def handle_start(message):
    """Ответ на /start"""
    bot.reply_to(message, "Привет! Я — Katana. Отправь JSON-команду, чтобы начать.")
    log_local_bot_event(f"/start received from {message.chat.id}")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Главный обработчик входящих сообщений."""
    # Make the handler async to use await for NLP service
    # However, telebot handlers are synchronous. We'll use asyncio.run() for the async part.
    # This is a simplification. For production, consider running the bot with an async framework
    # or managing the event loop more carefully if mixing sync and async extensively.

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
    elif command_type == "set_voice_style":
        args = command_data.get("args", {})
        if "lang" in args:
            lang = args["lang"]
            if lang is not None and isinstance(lang, str) and lang.strip(): # lang is present, not null, is a string and not empty
                user_voice_preferences[chat_id] = lang.strip()
                bot.reply_to(message, f"✅ Voice language set to: {user_voice_preferences[chat_id]}")
                log_local_bot_event(f"Set voice language for chat_id {chat_id} to {user_voice_preferences[chat_id]}")
            elif lang is None: # Explicitly set to null for clearing
                if chat_id in user_voice_preferences:
                    del user_voice_preferences[chat_id]
                    bot.reply_to(message, "✅ Voice preference cleared. Responses will be text only.")
                    log_local_bot_event(f"Cleared voice preference for chat_id {chat_id}")
                else:
                    bot.reply_to(message, "ℹ️ Voice preference was not set. Nothing to clear.")
                    log_local_bot_event(f"Attempted to clear voice preference for {chat_id}, but none was set.")
            else: # lang is present but empty string or not a string
                bot.reply_to(message, "❌ Error: 'lang' must be a valid language code string (e.g., 'en', 'es') or null to clear.")
                log_local_bot_event(f"Invalid 'lang' value ('{lang}') for set_voice_style from {chat_id}")
        else: # 'lang' key is missing from 'args'
            bot.reply_to(message, "❌ Error: 'set_voice_style' requires 'lang' in 'args'. Example: {\"lang\": \"en\"} or {\"lang\": null} to clear.")
            log_local_bot_event(f"Missing 'lang' key in 'args' for set_voice_style from {chat_id}")
        return
    elif command_type == "nlp_query":
        if "prompt" not in command_data.get("args", {}):
            error_msg = "❌ Error: 'nlp_query' type requires 'prompt' in 'args'."
            bot.reply_to(message, error_msg)
            log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text})")
            return

        prompt_text = command_data["args"]["prompt"]
        log_local_bot_event(f"Processing 'nlp_query' for chat_id {chat_id} with prompt: {prompt_text[:50]}...")

        nlp_response_text = None
        try:
            nlp_response_text = asyncio.run(nlp_service.get_chat_completion(prompt_text))
        except Exception as e:
            log_local_bot_event(f"Error processing nlp_query for {chat_id}: {e}")
            bot.reply_to(message, "🤖 Sorry, I encountered an issue processing your NLP request.")
            return

        if not nlp_response_text: # Should not happen if NLP service has fallbacks, but good to check
            log_local_bot_event(f"NLP query for {chat_id} resulted in empty response.")
            bot.reply_to(message, "🤖 Sorry, I could not get a response.")
            return

        # Check if user has a voice preference
        preferred_lang = user_voice_preferences.get(chat_id)
        if preferred_lang:
            log_local_bot_event(f"User {chat_id} has voice preference: {preferred_lang}. Attempting TTS.")
            audio_file_path = tts_service.text_to_speech(nlp_response_text, lang=preferred_lang)
            if audio_file_path:
                try:
                    with open(audio_file_path, 'rb') as audio_file:
                        bot.send_voice(chat_id, audio_file, reply_to_message_id=message.message_id)
                    log_local_bot_event(f"Sent TTS voice response to {chat_id}.")
                except Exception as e:
                    log_local_bot_event(f"Error sending voice message to {chat_id}: {e}")
                    bot.reply_to(message, f"(TTS audio failed, fallback to text): {nlp_response_text}")
                finally:
                    tts_service.cleanup_temp_file(audio_file_path) # Clean up the temp file
            else:
                log_local_bot_event(f"TTS conversion failed for {chat_id}. Sending text fallback.")
                bot.reply_to(message, f"(TTS failed, text response): {nlp_response_text}")
        else:
            # No voice preference, send as text
            bot.reply_to(message, nlp_response_text)
            log_local_bot_event(f"Sent NLP text response to {chat_id}: {nlp_response_text[:50]}...")
        return

    log_local_bot_event(f"Command type '{command_type}' not specifically handled, proceeding with default save.")

    # For other commands, save them compressed
    timestamp_str = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
    # Change file extension to .json.gz
    command_file_name = f"{timestamp_str}_{chat_id}.json.gz"
    
    module_name = command_data.get('module', 'telegram_general')
    module_command_dir = COMMAND_FILE_DIR / f"telegram_mod_{module_name}" if module_name != 'telegram_general' else COMMAND_FILE_DIR / 'telegram_general'
    module_command_dir.mkdir(parents=True, exist_ok=True)
    command_file_path = module_command_dir / command_file_name

    try:
        # Serialize json to string, then encode to bytes for gzip
        json_str = json.dumps(command_data, ensure_ascii=False, indent=2)
        json_bytes = json_str.encode('utf-8')

        with gzip.open(command_file_path, "wb") as f: # Open in binary write mode
            f.write(json_bytes)

        bot.reply_to(message, f"✅ Command received and saved (compressed) as `{command_file_path}`.")
        log_local_bot_event(f"Saved and compressed command from {chat_id} to {command_file_path}")
    except Exception as e:
        log_local_bot_event(f"Error saving/compressing command for {chat_id} to {command_file_path}: {e}")
        bot.reply_to(message, "❌ Error saving command.")


def cleanup_old_command_files(max_age_days=30):
    """Deletes command files older than max_age_days."""
    cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
    log_local_bot_event(f"Starting cleanup of command files older than {max_age_days} days (before {cutoff_date.isoformat()})...")
    cleaned_count = 0
    error_count = 0

    for item in COMMAND_FILE_DIR.glob('**/*.json.gz'): # Iterate through all .json.gz files recursively
        if item.is_file():
            try:
                file_mod_time_utc = datetime.utcfromtimestamp(item.stat().st_mtime)
                if file_mod_time_utc < cutoff_date:
                    item.unlink() # Delete the file
                    log_local_bot_event(f"Deleted old command file: {item}")
                    cleaned_count += 1
            except Exception as e:
                log_local_bot_event(f"Error deleting file {item}: {e}")
                error_count += 1
    
    log_local_bot_event(f"Cleanup finished. Deleted {cleaned_count} files. Encountered {error_count} errors.")


if __name__ == '__main__':
    log_local_bot_event("Bot starting...")
    # Perform cleanup on startup
    cleanup_old_command_files()
    # Note: For a continuously running bot, this cleanup might be better run on a schedule (e.g., daily)
    # using a library like 'schedule' or a separate cron job.

    bot.polling()
    log_local_bot_event("Bot stopped.")