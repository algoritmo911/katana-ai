import telebot
import json
import os
from pathlib import Path
from datetime import datetime
import subprocess # Added for run_katana_command
from katana.nlp_mapper import interpret # Added for NLP
import openai # Added for Whisper API
from dotenv import load_dotenv # Added for loading .env file
from katana.core.user_profile import UserProfile # Added for user personalization
from katana.adapters.local_file_adapter import LocalFileAdapter

# Load environment variables from .env file
load_dotenv()

# TODO: Get API token from environment variable or secrets manager
# Using a format-valid dummy token for testing purposes if no env var is set.
API_TOKEN = os.environ.get('TELEGRAM_API_TOKEN', '12345:dummytoken')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

bot = telebot.TeleBot(API_TOKEN)
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
# In a real application, this would be stored in a database or persistent storage.
BOT_STATS = {"commands_processed": 0}

def increment_command_count():
    """Increments the processed command counter."""
    BOT_STATS["commands_processed"] += 1

def get_bot_stats_message():
    """Returns a string with current bot statistics."""
    return f"Я уже обработал {BOT_STATS['commands_processed']} команд."


def log_local_bot_event(message):
    """Logs an event to the console and to the telegram.log file."""
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


# --- Katana Command Execution ---
def run_katana_command(command: str, message: telebot.types.Message) -> str:
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

def handle_log_event(command_data, chat_id):
    """Placeholder for handling 'log_event' commands."""
    log_local_bot_event(f"handle_log_event called for chat_id {chat_id} with data: {json.dumps(command_data)}")
    # Actual implementation for log_event will go here
    # TODO: Add more specific logging based on args if needed
    log_local_bot_event(f"Successfully processed 'log_event' for chat_id {chat_id}. Args: {json.dumps(command_data.get('args'))}")
    # bot.reply_to(message, "✅ 'log_event' received (placeholder).") # TODO: Add reply mechanism

def handle_mind_clearing(command_data, chat_id):
    """Placeholder for handling 'mind_clearing' commands."""
    log_local_bot_event(f"handle_mind_clearing called for chat_id {chat_id} with data: {json.dumps(command_data)}")
    # Actual implementation for mind_clearing will go here
    # TODO: Add more specific logging based on args if needed
    log_local_bot_event(f"Successfully processed 'mind_clearing' for chat_id {chat_id}. Args: {json.dumps(command_data.get('args'))}")
    # bot.reply_to(message, "✅ 'mind_clearing' received (placeholder).") # TODO: Add reply mechanism

# This will be the new text handler
@bot.message_handler(commands=['recommendations'])
def handle_recommendations(message):
    """Handles the /recommendations command."""
    user_id = message.from_user.id
    local_storage = LocalFileAdapter()
    profile_data = local_storage.load(user_id)
    if profile_data:
        # The user_id from the message should take precedence.
        profile_data.pop('user_id', None)
        user_profile = UserProfile(user_id=user_id, **profile_data)
    else:
        user_profile = UserProfile(user_id=user_id)

    recommendations = user_profile.get_command_recommendations()

    if not recommendations:
        bot.reply_to(message, "У меня пока нет рекомендаций для вас. Попробуйте использовать несколько команд, и я смогу вам что-нибудь предложить.")
        return

    response = "Вот несколько команд, которые вы часто используете:\n"
    for i, command in enumerate(recommendations, 1):
        response += f"{i}. `{command}`\n"

    bot.reply_to(message, response, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text_message(message):
    """Handles incoming text messages, attempting NLP interpretation first."""
    chat_id = message.chat.id
    user_id = message.from_user.id
    text = message.text
    username = get_username(message)
    time_greeting = get_time_of_day_greeting()

    # Get user profile
    local_storage = LocalFileAdapter()
    profile_data = local_storage.load(user_id)
    if profile_data:
        user_profile = UserProfile(user_id=user_id, **profile_data)
    else:
        user_profile = UserProfile(user_id=user_id)


    log_local_bot_event(f"Received text message from {username} ({chat_id}): {text}")
    increment_command_count() # Increment for any processed message

    # Add command to user's history and save profile
    user_profile.add_command_to_history(text)
    local_storage.save(user_id, user_profile.__dict__)

    # Attempt to interpret the text as a natural language command
    nlp_command_or_response = interpret(text)

    if nlp_command_or_response:
        log_to_file(f'[NLU] "{text}" → "{nlp_command_or_response}"')

        # Handle direct responses from NLP (e.g., "Привет! Как я могу помочь?")
        if nlp_command_or_response.startswith("Привет!"): # Simple check for greeting
            bot.send_message(chat_id, f"{time_greeting}, {username}! {nlp_command_or_response} {get_bot_stats_message()}")
            return

        # Handle API command keywords
        if nlp_command_or_response == "get_weather":
            # Placeholder for actual weather API call
            weather_info = "Сегодня солнечно, +25°C." # api.get_weather_data(location)
            bot.send_message(chat_id, f"{time_greeting}, {username}! {weather_info} {get_bot_stats_message()}")
            return
        if nlp_command_or_response == "get_joke":
            # Placeholder for actual joke API call
            joke_text = "Почему программисты всегда путают Хэллоуин и Рождество? Потому что OCT 31 == DEC 25." # api.get_joke_text()
            bot.send_message(chat_id, f"{time_greeting}, {username}! {joke_text} {get_bot_stats_message()}")
            return

        # For other NLP commands that are shell commands
        output = run_katana_command(nlp_command_or_response, message)
        bot.send_message(chat_id, f"{time_greeting}, {username}! 🧠 Понял. Выполняю:\n`{nlp_command_or_response}`\n\n{output}\n\n{get_bot_stats_message()}", parse_mode="Markdown")
        return

    # If not an NLP command, try to parse as JSON (old behavior)
    log_local_bot_event(f"No NLP command interpreted from '{text}'. Attempting JSON parse.")
    try:
        command_data = json.loads(text)
    except json.JSONDecodeError:
        # If it's not JSON either, then it's an unrecognized command
        fallback_message = (
            f"{time_greeting}, {username}. К сожалению, я не смог распознать вашу команду: \"{text}\". \n"
            "Пожалуйста, попробуйте переформулировать ваш запрос или используйте одну из известных мне команд. "
            "Если вы пытались отправить JSON-команду, проверьте ее формат. "
            f"{get_bot_stats_message()}"
        )
        bot.reply_to(message, fallback_message)
        log_local_bot_event(f"Invalid JSON and not an NLP command from {username} ({chat_id}): {text}")
        return

    # --- Existing JSON command processing logic starts here ---
    # (Copied and adapted from the original handle_message)
    # log_local_bot_event(f"Attempting to process as JSON command from {chat_id}: {text}") # Already logged above
    # Validate command_data fields
    required_fields = {
        "type": str,
        "module": str,
        "args": dict,
        "id": (str, int)  # id can be string or integer
    }

    for field, expected_type in required_fields.items():
        if field not in command_data:
            error_msg = f"Error: Missing required field '{field}'."
            bot.reply_to(message, error_msg)
            log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {text})")
            return
        # isinstance check for the field's type
        # For 'id', it can be str or int. For others, it's a single type.
        if field == "id":
            if not any(isinstance(command_data[field], t) for t in expected_type):
                error_msg = f"Error: Field '{field}' must be type {' or '.join(t.__name__ for t in expected_type)}. Got value '{command_data[field]}' of type {type(command_data[field]).__name__}."
                bot.reply_to(message, error_msg)
                log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {text})")
                return
        elif not isinstance(command_data[field], expected_type):
            error_msg = f"Error: Field '{field}' must be type {expected_type.__name__}. Got value '{command_data[field]}' of type {type(command_data[field]).__name__}."
            bot.reply_to(message, error_msg)
            log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {text})")
            return

    # Additional validation for 'module' and 'type' fields
    if not command_data['module'].strip():
        error_msg = f"Error: Field 'module' must be a non-empty string. Got value '{command_data['module']}'."
        bot.reply_to(message, error_msg)
        log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {text})")
        return

    if not command_data['type'].strip():
        error_msg = f"Error: Field 'type' must be a non-empty string. Got value '{command_data['type']}'."
        bot.reply_to(message, error_msg)
        log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {text})")
        return

    # Log successful validation
    log_local_bot_event(f"Successfully validated command from {chat_id}: {json.dumps(command_data)}")

    # Command routing based on 'type'
    command_type = command_data.get("type")

    if command_type == "log_event":
        handle_log_event(command_data, chat_id)
        bot.reply_to(message, "✅ 'log_event' processed (placeholder).")
        return
    elif command_type == "mind_clearing":
        handle_mind_clearing(command_data, chat_id)
        bot.reply_to(message, "✅ 'mind_clearing' processed (placeholder).")
        return

    # If type is not matched, proceed with default behavior (saving)
    log_local_bot_event(f"Command type '{command_type}' not specifically handled, proceeding with default save. Full command data: {json.dumps(command_data)}")

    # Save the command to a file
    log_local_bot_event(f"Attempting to save command from {chat_id}. Full command data: {json.dumps(command_data)}")
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
    user_id = message.from_user.id
    log_local_bot_event(f"Received voice message from {chat_id}. File ID: {message.voice.file_id}")

    # Get user profile
    local_storage = LocalFileAdapter()
    profile_data = local_storage.load(user_id)
    if profile_data:
        # The user_id from the message should take precedence.
        profile_data.pop('user_id', None)
        user_profile = UserProfile(user_id=user_id, **profile_data)
    else:
        user_profile = UserProfile(user_id=user_id)

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

            # Add command to user's history and save profile
            user_profile.add_command_to_history(transcribed_text)
            local_storage.save(user_id, user_profile.__dict__)

            # Create a new message object that looks like a text message
            # This allows reusing the handle_text_message logic
            # Some attributes of message might not be perfectly replicated, but core ones for handle_text_message should be.
            # Important: telebot.types.Message is complex. We only mock what's needed.
            # A cleaner way might be to refactor handle_text_message to accept text directly.
            # For now, this approach minimizes changes to existing text handling.

            # Mimic a text message to pass to handle_text_message
            # We need to ensure this mock message has all attributes handle_text_message expects
            mock_text_message = telebot.types.Message(
                message_id=message.message_id,
                from_user=message.from_user, # or message.chat if from_user is None in some contexts
                date=message.date,
                chat=message.chat,
                content_type='text',
                options=[], # Placeholder, may need adjustment
                json_string=json.dumps({'text': transcribed_text}) # Ensure 'text' is available
            )
            mock_text_message.text = transcribed_text # Explicitly set the text attribute

            bot.reply_to(message, f"🗣️ Распознано: \"{transcribed_text}\"")
            handle_text_message(mock_text_message) # Process as if it was a text message
        else:
            username = get_username(message)
            time_greeting = get_time_of_day_greeting()
            bot.reply_to(message, f"{time_greeting}, {username}. Не смог распознать речь в вашем голосовом сообщении. Пожалуйста, попробуйте еще раз, говорите четче. 🎙️ {get_bot_stats_message()}")
            log_local_bot_event(f"Transcription failed or returned empty for voice from {username} ({chat_id})")

    except Exception as e:
        username = get_username(message)
        time_greeting = get_time_of_day_greeting()
        bot.reply_to(message, f"{time_greeting}, {username}. При обработке вашего голосового сообщения произошла неожиданная ошибка. Попробуйте позже. 😥 {get_bot_stats_message()}")
        log_local_bot_event(f"Error processing voice message from {username} ({chat_id}): {e}")
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
