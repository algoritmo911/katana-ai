import telebot
import json # Still needed for mock message in voice handler, consider removing if mock is fully gone.
# Actually, json is used by telebot.types.Message for json_string. And potentially by OpenAI's library. Let's keep it.
import os
from pathlib import Path
from datetime import datetime
import openai # Added for Whisper API and GPT
from dotenv import load_dotenv # Added for loading .env file

# Load environment variables from .env file
load_dotenv()

# API Tokens and Bot Initialization
API_TOKEN = os.environ.get('TELEGRAM_API_TOKEN', '12345:dummytoken') # Dummy for local dev if not set
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

bot = telebot.TeleBot(API_TOKEN)

if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
else:
    print("[CRITICAL] OPENAI_API_KEY not found in environment variables. Voice recognition and GPT features WILL NOT WORK.")
    # Consider exiting if OpenAI key is critical and not found, or providing a fallback mode.

# --- Logging Setup ---
LOG_DIR = Path('logs')
LOG_DIR.mkdir(parents=True, exist_ok=True)
TELEGRAM_LOG_FILE = LOG_DIR / 'telegram.log'

# Directory for storing temporary voice files
VOICE_FILE_DIR = Path('voice_temp') # This was correctly here
VOICE_FILE_DIR.mkdir(parents=True, exist_ok=True)


def log_to_file(message_text, filename=TELEGRAM_LOG_FILE):
    """Appends a message to the specified log file."""
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.utcnow().isoformat()} | {message_text}\n")

def log_local_bot_event(event_description):
    """Logs an event to the console and to the telegram.log file."""
    full_log_message = f"[BOT_EVENT] {event_description}"
    print(f"{datetime.utcnow().isoformat()} | {full_log_message}")
    log_to_file(full_log_message)

# --- GPT Interaction ---
def get_gpt_response(user_text: str) -> str:
    """
    Sends user_text to OpenAI GPT API and returns the response.
    """
    log_local_bot_event(f"Sending to GPT: '{user_text}'")
    if not OPENAI_API_KEY:
        log_local_bot_event("OpenAI API key not configured. Cannot get GPT response.")
        return "⚠️ GPT服务当前不可用 (API key missing)."

    try:
        # Using a simple prompt, adjust as needed.
        # Consider adding context or system messages if required for better responses.
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", # Or "gpt-4" if available and preferred
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_text}
            ]
        )
        gpt_response = response.choices[0].message.content.strip()
        log_local_bot_event(f"Received from GPT: '{gpt_response}'")
        return gpt_response
    except openai.APIError as e:
        log_local_bot_event(f"OpenAI API Error during GPT call: {e}")
        return f"🤖 Ошибка при обращении к ИИ: {e}"
    except Exception as e:
        log_local_bot_event(f"Unexpected error during GPT call: {e}")
        return "🤖 Произошла непредвиденная ошибка при обработке вашего запроса."


# --- Text Message Handler ---
@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text_message(message):
    """Handles incoming text messages by sending them to GPT."""
    chat_id = message.chat.id
    text = message.text.strip()

    log_to_file(f"USER_MESSAGE | ChatID: {chat_id} | Text: \"{text}\"")
    log_local_bot_event(f"Received text message from {chat_id}: \"{text}\"")

    # System command handling
    if text.lower() == "/start":
        log_local_bot_event(f"Processing /start command for chat_id {chat_id}")
        # Basic welcome message, can be expanded.
        # Consider adding a prompt to the system message of get_gpt_response for /start if more dynamic welcome is needed.
        # For now, keeping it simple and local.
        start_message = (
            "👋 Привет! Я ваш ИИ-ассистент.\n"
            "Просто отправьте мне сообщение или голосовую заметку, и я постараюсь помочь.\n\n"
            "Доступные команды:\n"
            "/help - Показать это сообщение\n"
            "/status - Проверить мой статус"
        )
        bot.send_message(chat_id, start_message)
        log_to_file(f"SYSTEM_COMMAND | ChatID: {chat_id} | Command: /start | Response: \"{start_message}\"")
        return
    elif text.lower() == "/help":
        log_local_bot_event(f"Processing /help command for chat_id {chat_id}")
        help_message = (
            "Как я могу помочь:\n"
            "- Отправьте мне любой текстовый вопрос или утверждение.\n"
            "- Отправьте голосовое сообщение, я его расшифрую и отвечу.\n"
            "- /status: Проверить, работаю ли я.\n"
            "- /start: Показать приветственное сообщение.\n\n"
            "Я использую GPT для генерации ответов, так что просто говорите со мной естественно!"
        )
        bot.send_message(chat_id, help_message)
        log_to_file(f"SYSTEM_COMMAND | ChatID: {chat_id} | Command: /help | Response: \"{help_message}\"")
        return
    elif text.lower() == "/status":
        log_local_bot_event(f"Processing /status command for chat_id {chat_id}")
        status_message = "✅ Я в порядке и готов к работе!"
        if not OPENAI_API_KEY:
            status_message = "⚠️ Я работаю, но функция ИИ отключена (проблема с API ключом)."
        bot.send_message(chat_id, status_message)
        log_to_file(f"SYSTEM_COMMAND | ChatID: {chat_id} | Command: /status | Response: \"{status_message}\"")
        return

    # If not a system command, proceed with GPT
    ai_response = get_gpt_response(text)
    log_to_file(f"AI_RESPONSE | ChatID: {chat_id} | Response: \"{ai_response}\"")
    bot.send_message(chat_id, ai_response)


# --- Voice Processing ---
def get_text_from_voice(voice_file_path: str) -> str | None:
    """
    Transcribes voice using OpenAI Whisper API.
    Returns the transcribed text or None if an error occurs.
    """
    if not OPENAI_API_KEY:
        log_local_bot_event("OpenAI API key not configured. Cannot process voice.")
        return None

    try:
        log_local_bot_event(f"Sending voice file {voice_file_path} to OpenAI Whisper API...")
        with open(voice_file_path, "rb") as audio_file:
            transcription = openai.Audio.transcribe("whisper-1", audio_file)
        text = transcription.get('text')
        if text:
            log_local_bot_event(f"Voice transcribed successfully: '{text}'")
            return text.strip()
        else:
            log_local_bot_event("Voice transcription returned no text.")
            return None
    except openai.APIError as e:
        log_local_bot_event(f"OpenAI API Error during voice transcription: {e}")
        return None
    except Exception as e:
        log_local_bot_event(f"Unexpected error during voice transcription: {e}")
        return None

# --- Voice Message Handler ---
VOICE_FILE_DIR = Path('voice_temp')
VOICE_FILE_DIR.mkdir(parents=True, exist_ok=True)

@bot.message_handler(content_types=['voice'])
def handle_voice_message(message):
    """Handles incoming voice messages."""
    chat_id = message.chat.id
    log_local_bot_event(f"Received voice message from {chat_id}. File ID: {message.voice.file_id}")

    if not OPENAI_API_KEY:
        bot.reply_to(message, "⚠️ Распознавание голоса не настроено на сервере.")
        log_local_bot_event("Voice recognition skipped: OpenAI API key not configured.")
        return

    try:
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        # Save the downloaded file temporarily
        temp_voice_path = VOICE_FILE_DIR / f"{message.voice.file_id}.ogg" # Telegram voice notes are often in ogg format
        with open(temp_voice_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        log_local_bot_event(f"Voice file saved temporarily to {temp_voice_path}")

        transcribed_text = get_text_from_voice(str(temp_voice_path))

        if transcribed_text:
            log_local_bot_event(f"Voice from {chat_id} transcribed to: '{transcribed_text}'")
            # Create a new message object that looks like a text message
            # This allows reusing the handle_text_message logic
            # Some attributes of message might not be perfectly replicated, but core ones for handle_text_message should be.
            # Important: telebot.types.Message is complex. We only mock what's needed.
            # A cleaner way might be to refactor handle_text_message to accept text directly.
            # For now, this approach minimizes changes to existing text handling.
            # No longer need to mock a message, just process the text.
            bot.reply_to(message, f"🗣️ Распознано: \"{transcribed_text}\"")
            log_to_file(f"USER_MESSAGE (VOICE) | ChatID: {chat_id} | Transcribed: \"{transcribed_text}\"")

            # Directly send transcribed text to GPT processing
            ai_response = get_gpt_response(transcribed_text)
            log_to_file(f"AI_RESPONSE (from VOICE) | ChatID: {chat_id} | Response: \"{ai_response}\"")
            bot.send_message(chat_id, ai_response)

        else:
            bot.reply_to(message, "Не понял, повтори, пожалуйста. 🎙️ Не удалось распознать речь.")
            log_local_bot_event(f"Transcription failed or returned empty for voice from {chat_id}")

    except Exception as e:
        bot.reply_to(message, "Произошла ошибка при обработке голосового сообщения. 😥")
        log_local_bot_event(f"Error processing voice message from {chat_id}: {e}")
    finally:
        # Clean up the temporary file
        if 'temp_voice_path' in locals() and temp_voice_path.exists():
            try:
                os.remove(temp_voice_path)
                log_local_bot_event(f"Temporary voice file {temp_voice_path} deleted.")
            except OSError as e_os:
                log_local_bot_event(f"Error deleting temporary voice file {temp_voice_path}: {e_os}")


if __name__ == '__main__':
    log_local_bot_event("Bot starting...")
    bot.polling()
    log_local_bot_event("Bot stopped.")
