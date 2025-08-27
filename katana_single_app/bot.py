import asyncio
import json
import os
from pathlib import Path
from datetime import datetime
import subprocess # Added for run_katana_command
# from nlp_mapper import interpret # DEPRECATED: Replaced by AbstractNLPService
from katana_single_app.services.nlp_service import RuleBasedNLPService, Intent
import openai # Added for Whisper API
from dotenv import load_dotenv # Added for loading .env file
from telebot import async_telebot

# Load environment variables from .env file
load_dotenv()

# --- Service Initialization ---
# In a real DI container, this would be injected. For now, a global instance.
nlp_service = RuleBasedNLPService()


# --- Bot Configuration ---
API_TOKEN = os.environ.get('TELEGRAM_API_TOKEN', '12345:dummytoken')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

bot = async_telebot.AsyncTeleBot(API_TOKEN)
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
else:
    print("[WARNING] OPENAI_API_KEY not found in environment variables. Voice recognition will not work.")

# Directory for storing command files
COMMAND_FILE_DIR = Path('commands')
COMMAND_FILE_DIR.mkdir(parents=True, exist_ok=True)

# --- Logging Setup ---
LOG_DIR = Path('logs')
LOG_DIR.mkdir(parents=True, exist_ok=True)
TELEGRAM_LOG_FILE = LOG_DIR / 'telegram.log'

def log_to_file(message, filename=TELEGRAM_LOG_FILE):
    """Appends a message to the specified log file."""
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.utcnow().isoformat()} | {message}\n")

# --- Bot Statistics (Placeholder) ---
BOT_STATS = {"commands_processed": 0}

def increment_command_count():
    """Increments the processed command counter."""
    BOT_STATS["commands_processed"] += 1

def get_bot_stats_message():
    """Returns a string with current bot statistics."""
    return f"Я уже обработал {BOT_STATS['commands_processed']} команд."


def log_local_bot_event(message):
    """Logs an event to the console and to the telegram.log file."""
    # In the future, this should use a proper structured logger with trace_id
    print(f"[BOT EVENT] {datetime.utcnow().isoformat()}: {message}")
    log_to_file(f"[BOT_EVENT] {message}")

# --- Dynamic Response Helpers ---
def get_time_of_day_greeting():
    """Returns a greeting based on the current time of day."""
    current_hour = datetime.now().hour
    if 5 <= current_hour < 12:
        return "Доброе утро"
    elif 12 <= current_hour < 17:
        return "Добрый день"
    elif 17 <= current_hour < 22:
        return "Добрый вечер"
    else:
        return "Доброй ночи"

def get_username(message):
    """Extracts username from message, defaults to 'Пользователь'."""
    if message.from_user:
        if message.from_user.username:
            return f"@{message.from_user.username}"
        elif message.from_user.first_name:
            return message.from_user.first_name
    return "Пользователь"


# --- Katana Command Execution (To be refactored into Action Cortex) ---
def run_katana_command(command: str, message: async_telebot.types.Message) -> str:
    """
    Executes a shell command and returns its output.
    This is a simplified placeholder. In a real scenario, this would interact
    with a more complex 'katana_agent' or similar.
    """
    log_local_bot_event(f"Running katana command: {command}")
    try:
        # Using shell=True for simplicity with complex commands like pipes.
        # Be cautious with shell=True in production due to security risks.
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True, timeout=30)
        output = result.stdout.strip()
        if result.stderr.strip():
            output += f"\nStderr:\n{result.stderr.strip()}"
        log_local_bot_event(f"Command output: {output}")
        return output
    except subprocess.CalledProcessError as e:
        error_message = f"Error executing command '{command}': {e.stderr.strip()}"
        log_local_bot_event(error_message)
        return error_message
    except subprocess.TimeoutExpired:
        error_message = f"Command '{command}' timed out."
        log_local_bot_event(error_message)
        return error_message
    except Exception as e:
        error_message = f"An unexpected error occurred while running command '{command}': {str(e)}"
        log_local_bot_event(error_message)
        return error_message

# --- JSON Command Handlers (To be refactored into Cognitive Core) ---
async def handle_log_event(command_data, chat_id, message):
    """Placeholder for handling 'log_event' commands."""
    log_local_bot_event(f"handle_log_event called for chat_id {chat_id} with data: {json.dumps(command_data)}")
    log_local_bot_event(f"Successfully processed 'log_event' for chat_id {chat_id}. Args: {json.dumps(command_data.get('args'))}")
    await bot.reply_to(message, "✅ 'log_event' processed (placeholder).")

async def handle_mind_clearing(command_data, chat_id, message):
    """Placeholder for handling 'mind_clearing' commands."""
    log_local_bot_event(f"handle_mind_clearing called for chat_id {chat_id} with data: {json.dumps(command_data)}")
    log_local_bot_event(f"Successfully processed 'mind_clearing' for chat_id {chat_id}. Args: {json.dumps(command_data.get('args'))}")
    await bot.reply_to(message, "✅ 'mind_clearing' processed (placeholder).")


# --- Main Text Message Handler ---
@bot.message_handler(func=lambda message: True, content_types=['text'])
async def handle_text_message(message):
    """Handles incoming text messages, attempting NLP interpretation first."""
    chat_id = message.chat.id
    text = message.text
    username = get_username(message)
    time_greeting = get_time_of_day_greeting()

    log_local_bot_event(f"Received text message from {username} ({chat_id}): '{text}'")
    increment_command_count()

    # PHASE 1: Use the NLP Service to parse intent.
    intent = await nlp_service.parse_intent(text)
    log_local_bot_event(f"Intent parsed: {intent!r}") # Using !r for detailed repr

    # According to CH-L1-04, we just log the intent for now.
    # The old logic of checking nlp_command_or_response is removed.
    # We will add logic here in later phases to dispatch commands based on intent.

    # For now, we will respond with a simple acknowledgement that the intent was logged.
    # This proves the new NLP layer is integrated.
    if intent.name != "unknown":
        # This is a temporary response to show the system is working.
        # This will be replaced by the Action Cortex in Phase 4.
        temp_response = f"{time_greeting}, {username}. Ваше намерение '{intent.name}' было распознано и залогировано. Скоро я научусь на него отвечать. {get_bot_stats_message()}"
        await bot.send_message(chat_id, temp_response)
        return

    # If the intent is 'unknown', we fall back to the old JSON parsing logic.
    log_local_bot_event(f"Intent was 'unknown'. Attempting JSON parse for legacy command.")
    try:
        command_data = json.loads(text)
    except json.JSONDecodeError:
        fallback_message = (
            f"{time_greeting}, {username}. К сожалению, я не смог распознать вашу команду: \"{text}\". \n"
            "Пожалуйста, попробуйте переформулировать ваш запрос. "
            f"{get_bot_stats_message()}"
        )
        await bot.reply_to(message, fallback_message)
        log_local_bot_event(f"Unrecognized command and invalid JSON from {username} ({chat_id}): {text}")
        return

    # --- Existing JSON command processing logic starts here ---
    required_fields = {"type": str, "module": str, "args": dict, "id": (str, int)}
    for field, expected_type in required_fields.items():
        if field not in command_data:
            error_msg = f"Error: Missing required field '{field}'."
            await bot.reply_to(message, error_msg)
            return
        if not isinstance(command_data[field], expected_type if not isinstance(expected_type, tuple) else expected_type):
             error_msg = f"Error: Field '{field}' must be type {expected_type.__name__}. Got value '{command_data[field]}' of type {type(command_data[field]).__name__}."
             if isinstance(expected_type, tuple):
                 error_msg = f"Error: Field '{field}' must be type {' or '.join(t.__name__ for t in expected_type)}. Got value '{command_data[field]}' of type {type(command_data[field]).__name__}."
             await bot.reply_to(message, error_msg)
             return

    log_local_bot_event(f"Successfully validated JSON command from {chat_id}: {json.dumps(command_data)}")
    command_type = command_data.get("type")

    if command_type == "log_event":
        await handle_log_event(command_data, chat_id, message)
        return
    elif command_type == "mind_clearing":
        await handle_mind_clearing(command_data, chat_id, message)
        return

    log_local_bot_event(f"JSON Command type '{command_type}' not specifically handled, proceeding with default save.")
    timestamp_str = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
    command_file_name = f"{timestamp_str}_{chat_id}.json"
    module_name = command_data.get('module', 'telegram_general')
    module_command_dir = COMMAND_FILE_DIR / f"telegram_mod_{module_name}"
    module_command_dir.mkdir(parents=True, exist_ok=True)
    command_file_path = module_command_dir / command_file_name

    with open(command_file_path, "w", encoding="utf-8") as f:
        json.dump(command_data, f, ensure_ascii=False, indent=2)

    await bot.reply_to(message, f"✅ Legacy JSON command received and saved as `{command_file_path}`.")
    log_local_bot_event(f"Saved legacy command from {chat_id} to {command_file_path}")


# --- Voice Processing ---
async def get_text_from_voice(voice_file_path: str) -> str | None:
    """Transcribes voice using OpenAI Whisper API."""
    if not OPENAI_API_KEY:
        log_local_bot_event("OpenAI API key not configured. Cannot process voice.")
        return None
    try:
        log_local_bot_event(f"Sending voice file {voice_file_path} to OpenAI Whisper API...")
        with open(voice_file_path, "rb") as audio_file:
            # Note: openai.Audio.transcribe is not async, so we run it in a thread
            loop = asyncio.get_running_loop()
            transcription = await loop.run_in_executor(None, lambda: openai.Audio.transcribe("whisper-1", audio_file))
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

VOICE_FILE_DIR = Path('voice_temp')
VOICE_FILE_DIR.mkdir(parents=True, exist_ok=True)

@bot.message_handler(content_types=['voice'])
async def handle_voice_message(message):
    """Handles incoming voice messages."""
    chat_id = message.chat.id
    username = get_username(message)
    log_local_bot_event(f"Received voice message from {username} ({chat_id}). File ID: {message.voice.file_id}")

    if not OPENAI_API_KEY:
        await bot.reply_to(message, "⚠️ Распознавание голоса не настроено на сервере.")
        return

    try:
        file_info = await bot.get_file(message.voice.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)

        temp_voice_path = VOICE_FILE_DIR / f"{message.voice.file_id}.ogg"
        with open(temp_voice_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        transcribed_text = await get_text_from_voice(str(temp_voice_path))

        if transcribed_text:
            await bot.reply_to(message, f"🗣️ Распознано: \"{transcribed_text}\"")
            # Mimic a text message to pass to the text handler
            mock_text_message = async_telebot.types.Message(
                message_id=message.message_id, from_user=message.from_user,
                date=message.date, chat=message.chat, content_type='text', options=[],
                json_string=json.dumps({'text': transcribed_text})
            )
            mock_text_message.text = transcribed_text
            await handle_text_message(mock_text_message)
        else:
            await bot.reply_to(message, f"{get_time_of_day_greeting()}, {username}. Не смог распознать речь. 🎙️")
    except Exception as e:
        log_local_bot_event(f"Error processing voice message from {username} ({chat_id}): {e}")
        await bot.reply_to(message, f"{get_time_of_day_greeting()}, {username}. Произошла ошибка при обработке голоса. 😥")
    finally:
        if 'temp_voice_path' in locals() and temp_voice_path.exists():
            os.remove(temp_voice_path)


if __name__ == '__main__':
    log_local_bot_event("Bot starting in async mode...")
    asyncio.run(bot.polling())
    log_local_bot_event("Bot stopped.")
