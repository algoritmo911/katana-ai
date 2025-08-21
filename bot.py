import telebot.async_telebot # Use AsyncTeleBot
import asyncio # For asyncio operations
import json
import os
from pathlib import Path
from datetime import datetime, timezone
import subprocess # Added for run_katana_command
import time # Added for performance timing
from nlp_mapper import interpret # Added for NLP
import openai # Added for Whisper API
from dotenv import load_dotenv # Added for loading .env file
from katana.katana_agent import KatanaAgent # Import KatanaAgent
from katana.decorators.trace_command import trace_command # Import the decorator
from katana.logging.telemetry_logger import log_command_telemetry # Import the telemetry logger

# Load environment variables from .env file
load_dotenv()

# TODO: Get API token from environment variable or secrets manager
# Using a format-valid dummy token for testing purposes if no env var is set.
API_TOKEN = os.environ.get('TELEGRAM_API_TOKEN', '12345:dummytoken')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

BOT_START_TIME = datetime.now(timezone.utc) # For uptime calculation

bot = telebot.async_telebot.AsyncTeleBot(API_TOKEN) # Use AsyncTeleBot
katana_agent_instance = KatanaAgent() # Instantiate KatanaAgent

if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
else:
    print("[WARNING] OPENAI_API_KEY not found in environment variables. Voice recognition and GPT features will not work.")

# Directory for storing command files
COMMAND_FILE_DIR = Path('commands')
COMMAND_FILE_DIR.mkdir(parents=True, exist_ok=True)

# --- Logging Setup ---
LOG_DIR = Path('logs')
LOG_DIR.mkdir(parents=True, exist_ok=True)
GENERAL_LOG_FILE = LOG_DIR / 'telegram.log' # Renamed for clarity
COMMAND_LOG_FILE = LOG_DIR / 'commands.log'

# Function to log command-specific structured data
def log_command_event(message: str):
    """Appends a structured command message to the command_events.log file."""
    with open(COMMAND_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} | {message}\n")

# Dictionary to store active GPT streaming tasks and their cancellation events
# Key: chat_id, Value: tuple(asyncio.Task, asyncio.Event, telegram_message_id_being_edited)
active_gpt_streams = {}

# --- Command Registry ---
# Stores command_name: {"handler": handler_function, "description": "Command description"}
_command_registry = {}

def register_command(command_name: str, handler, description: str):
    """Registers a slash command."""
    if command_name.startswith('/'):
        command_name = command_name[1:] # Store without leading slash for consistency
    _command_registry[command_name] = {"handler": handler, "description": description}
    log_local_bot_event(f"Command '{command_name}' registered with description: '{description}'")

def unregister_command(command_name: str):
    """Unregisters a slash command."""
    if command_name.startswith('/'):
        command_name = command_name[1:]
    if command_name in _command_registry:
        del _command_registry[command_name]
        log_local_bot_event(f"Command '{command_name}' unregistered.")
        return True
    log_local_bot_event(f"Command '{command_name}' not found in registry for unregistration.")
    return False

def get_command_handler(command_name: str):
    """Retrieves the handler for a registered command."""
    if command_name.startswith('/'):
        command_name = command_name[1:]
    return _command_registry.get(command_name)

def get_all_commands() -> dict:
    """Retrieves all registered commands and their descriptions."""
    return {cmd: data["description"] for cmd, data in _command_registry.items()}

# --- Conversation History Management ---
chat_histories = {}  # Stores conversation history for each chat_id
MAX_HISTORY_LENGTH = 20 # Max number of messages (user + assistant) to keep per chat

def add_to_history(chat_id: int, role: str, content: str):
    """Adds a message to the chat's history, maintaining max length."""
    if chat_id not in chat_histories:
        chat_histories[chat_id] = []

    chat_histories[chat_id].append({"role": role, "content": content})

    # Trim history if it exceeds max length
    if len(chat_histories[chat_id]) > MAX_HISTORY_LENGTH:
        # Keep the most recent MAX_HISTORY_LENGTH messages
        chat_histories[chat_id] = chat_histories[chat_id][-MAX_HISTORY_LENGTH:]

def get_history(chat_id: int) -> list:
    """Retrieves the history for a chat_id, or an empty list if none."""
    return chat_histories.get(chat_id, [])

def log_to_general_file(message, filename=GENERAL_LOG_FILE):
    """Appends a message to the general log file."""
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} | {message}\n")

def log_local_bot_event(message):
    """Logs an event to the console and to the general log file."""
    print(f"[BOT EVENT] {datetime.now(timezone.utc).isoformat()}: {message}")
    log_to_general_file(f"[BOT_EVENT] {message}")

# --- Katana Command Execution ---
async def run_katana_command(command: str) -> str:
    """
    Executes a shell command asynchronously, logs its telemetry, and returns its output.
    """
    command_name = "nlp_shell_command"
    start_time = time.perf_counter()
    success = False
    error_obj = None
    output = ""

    log_local_bot_event(f"Running katana command: {command}")
    try:
        import functools
        loop = asyncio.get_event_loop()
        proc_result = await loop.run_in_executor(
            None,
            functools.partial(
                subprocess.run,
                command,
                shell=True,
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )
        )
        output = proc_result.stdout.strip()
        if proc_result.stderr.strip():
            output += f"\nStderr:\n{proc_result.stderr.strip()}"
        success = True
        log_local_bot_event(f"Command output: {output}")
        return output
    except subprocess.CalledProcessError as e:
        error_obj = e
        output = f"Error executing command '{command}': {e.stderr.strip() if e.stderr else 'No stderr'}"
        log_local_bot_event(output)
        return output
    except subprocess.TimeoutExpired as e:
        error_obj = e
        output = f"Command '{command}' timed out."
        log_local_bot_event(output)
        return output
    except Exception as e:
        error_obj = e
        output = f"An unexpected error occurred while running command '{command}': {str(e)}"
        log_local_bot_event(output)
        return output
    finally:
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        log_command_telemetry(
            command_name=command_name,
            args=(command,), # Pass the executed command as an argument
            kwargs={},
            success=success,
            result=output, # Log the stdout/stderr output as the result
            error=error_obj,
            execution_time=execution_time
        )

async def handle_log_event(command_data, chat_id):
    """Placeholder for handling 'log_event' commands."""
    log_local_bot_event(f"handle_log_event called for chat_id {chat_id} with data: {json.dumps(command_data)}")
    # Actual implementation for log_event will go here
    # TODO: Add more specific logging based on args if needed
    log_local_bot_event(f"Successfully processed 'log_event' for chat_id {chat_id}. Args: {json.dumps(command_data.get('args'))}")
    # await bot.reply_to(message, "✅ 'log_event' received (placeholder).") # TODO: Add reply mechanism

async def handle_mind_clearing(command_data, chat_id):
    """Placeholder for handling 'mind_clearing' commands."""
    log_local_bot_event(f"handle_mind_clearing called for chat_id {chat_id} with data: {json.dumps(command_data)}")
    # Actual implementation for mind_clearing will go here
    # TODO: Add more specific logging based on args if needed
    log_local_bot_event(f"Successfully processed 'mind_clearing' for chat_id {chat_id}. Args: {json.dumps(command_data.get('args'))}")
    # await bot.reply_to(message, "✅ 'mind_clearing' received (placeholder).") # TODO: Add reply mechanism

# --- JSON Command Tracing ---
async def trace_json_command(command_data, chat_id, command_logic_coro):
    """
    A wrapper to trace the execution of JSON-based commands.
    It logs telemetry data such as execution time, success/failure, and arguments.
    """
    command_name = f"json_command.{command_data.get('module', 'unknown')}.{command_data.get('type', 'unknown')}"
    start_time = time.perf_counter()
    success = False
    error_obj = None
    result = None

    try:
        # The actual work is done by awaiting the passed coroutine
        result = await command_logic_coro
        success = True
        return result
    except Exception as e:
        error_obj = e
        log_local_bot_event(f"Error processing JSON command {command_name} for chat {chat_id}: {e}")
        # Re-raise the exception so the caller can handle it (e.g., send a reply to the user)
        raise
    finally:
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        log_command_telemetry(
            command_name=command_name,
            args=(),  # Positional args are not used for JSON commands
            kwargs=command_data,  # Log the entire JSON payload
            success=success,
            result=result,
            error=error_obj,
            execution_time=execution_time
        )

# --- Unified Message Processing ---
async def process_user_message(chat_id: int, text: str, original_message: telebot.types.Message):
    """
    Processes user text, whether from a direct text message or transcribed voice.
    Handles NLP, JSON commands, or falls back to GPT.
    """
    log_local_bot_event(f"Processing user message for chat {chat_id}: '{text[:100]}...'")

    # Attempt to interpret the text as a natural language command
    nlp_command = interpret(text)

    if nlp_command:
        # This part is a bit of a hack, as log_to_file is not defined. I'll comment it out.
        # log_to_file(f'[NLU] "{text}" → "{nlp_command}" for chat {chat_id}')
        output = await run_katana_command(nlp_command)
        # Use original_message for reply context if available, otherwise send to chat_id
        try:
            await bot.reply_to(original_message, f"🧠 Понял. Выполняю:\n`{nlp_command}`\n\n{output}", parse_mode="Markdown")
        except Exception as e: # Fallback if reply_to fails (e.g. original_message is None or from a different context)
            log_local_bot_event(f"Failed to reply_to original_message for NLP command, sending new message. Error: {e}")
            await bot.send_message(chat_id, f"🧠 Понял. Выполняю:\n`{nlp_command}`\n\n{output}", parse_mode="Markdown")
        return

    # If not an NLP command, try to parse as JSON
    log_local_bot_event(f"No NLP command interpreted from '{text}' for chat {chat_id}. Attempting JSON parse.")
    try:
        command_data = json.loads(text)
        # --- JSON command processing logic (adapted from handle_text_message) ---
        required_fields = {
            "type": str, "module": str, "args": dict, "id": (str, int)
        }
        for field, expected_type in required_fields.items():
            if field not in command_data:
                error_msg = f"Error: Missing required field '{field}'."
                await bot.reply_to(original_message, error_msg)
                log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {text})")
                return
            if field == "id":
                if not any(isinstance(command_data[field], t) for t in expected_type):
                    error_msg = f"Error: Field '{field}' must be type {' or '.join(t.__name__ for t in expected_type)}. Got value '{command_data[field]}' of type {type(command_data[field]).__name__}."
                    await bot.reply_to(original_message, error_msg)
                    log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {text})")
                    return
            elif not isinstance(command_data[field], expected_type):
                error_msg = f"Error: Field '{field}' must be type {expected_type.__name__}. Got value '{command_data[field]}' of type {type(command_data[field]).__name__}."
                await bot.reply_to(original_message, error_msg)
                log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {text})")
                return

        if not command_data['module'].strip() or not command_data['type'].strip():
            error_msg = "Error: Fields 'module' and 'type' must be non-empty strings."
            if not command_data['module'].strip():
                 error_msg = f"Error: Field 'module' must be a non-empty string. Got value '{command_data['module']}'."
            elif not command_data['type'].strip():
                 error_msg = f"Error: Field 'type' must be a non-empty string. Got value '{command_data['type']}'."
            await bot.reply_to(original_message, error_msg)
            log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {text})")
            return

        log_local_bot_event(f"Successfully validated JSON command from {chat_id}: {json.dumps(command_data)}")

        # --- Traceable JSON Command Execution ---
        try:
            command_type = command_data.get("type")

            if command_type == "log_event":
                await trace_json_command(
                    command_data, chat_id,
                    handle_log_event(command_data, chat_id)
                )
                await bot.reply_to(original_message, "✅ 'log_event' processed.")

            elif command_type == "mind_clearing":
                await trace_json_command(
                    command_data, chat_id,
                    handle_mind_clearing(command_data, chat_id)
                )
                await bot.reply_to(original_message, "✅ 'mind_clearing' processed.")

            else:
                # Default action: save to file, but now wrapped in the tracer
                log_local_bot_event(f"Command type '{command_type}' not specifically handled, proceeding with default save.")

                async def save_command_coro():
                    loop = asyncio.get_event_loop()
                    timestamp_str = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
                    command_file_name = f"{timestamp_str}_{chat_id}.json"
                    module_name = command_data.get('module', 'telegram_general')
                    module_command_dir_name = f"telegram_mod_{module_name}" if module_name != 'telegram_general' else 'telegram_general'

                    def _save_command_file_sync():
                        module_command_dir = COMMAND_FILE_DIR / module_command_dir_name
                        module_command_dir.mkdir(parents=True, exist_ok=True)
                        command_file_path_res = module_command_dir / command_file_name
                        with open(command_file_path_res, "w", encoding="utf-8") as f:
                            json.dump(command_data, f, ensure_ascii=False, indent=2)
                        return str(command_file_path_res)

                    command_file_path = await loop.run_in_executor(None, _save_command_file_sync)
                    log_local_bot_event(f"Saved command from {chat_id} to {command_file_path}")
                    return command_file_path

                saved_path = await trace_json_command(
                    command_data, chat_id,
                    save_command_coro()
                )
                await bot.reply_to(original_message, f"✅ Command received and saved as `{saved_path}`.")

        except Exception as e:
            # This will catch errors from both the tracer and the command logic itself
            # The tracer will have already logged the error, so we just need to inform the user.
            await bot.reply_to(original_message, "⚠️ An error occurred while processing your command.")

        return

    except json.JSONDecodeError:
        # Not NLP, not JSON -> Route to KatanaAgent
        log_local_bot_event(f"Text from {chat_id} ('{text[:50]}...') is not NLP or JSON. Routing to KatanaAgent.")

        # Add user's message to history
        add_to_history(chat_id, "user", text)
        current_chat_history = get_history(chat_id)

        try:
            # Get response from KatanaAgent
            # Note: KatanaAgent's get_response is synchronous in the current plan.
            # If it were async, we would 'await' it.
            # For now, we run it in executor to prevent blocking the main async loop if it becomes complex later.
            loop = asyncio.get_event_loop()
            katana_response_text = await loop.run_in_executor(
                None,  # Uses the default ThreadPoolExecutor
                katana_agent_instance.get_response,
                text,  # current user message
                current_chat_history # history *including* current user message
            )

            if katana_response_text:
                # Add Katana's response to history
                add_to_history(chat_id, "assistant", katana_response_text)
                # Send Katana's response to the user
                if original_message:
                    await bot.reply_to(original_message, katana_response_text)
                else: # Should not happen for user messages, but as a fallback
                    await bot.send_message(chat_id, katana_response_text)
                log_local_bot_event(f"KatanaAgent response sent to {chat_id}: '{katana_response_text[:100]}...'")
            else:
                log_local_bot_event(f"KatanaAgent returned no response for {chat_id}.")
                # Optionally send a message like "Katana has nothing to say."
                # For now, just log.

        except Exception as e:
            log_local_bot_event(f"Error interacting with KatanaAgent for chat {chat_id}: {e}")
            error_reply = "⚠️ Error communicating with Katana."
            if original_message:
                await bot.reply_to(original_message, error_reply)
            else:
                await bot.send_message(chat_id, error_reply)
        return # KatanaAgent has handled the message.

# This will be the new text handler
@bot.message_handler(func=lambda message: True, content_types=['text'])
async def handle_text_message(message):
    """Handles incoming text messages by routing to the unified processor."""
    chat_id = message.chat.id
    text = message.text
    log_local_bot_event(f"Received text message from {chat_id}: {text}")
    await process_user_message(chat_id, text, message)


# --- Voice Processing ---
async def get_text_from_voice(voice_file_path: str) -> str | None:
    """
    Transcribes voice using OpenAI Whisper API.
    Returns the transcribed text or None if an error occurs.
    """
    if not OPENAI_API_KEY:
        log_local_bot_event("OpenAI API key not configured. Cannot process voice.")
        return None

    try:
        import functools
        loop = asyncio.get_event_loop()
        log_local_bot_event(f"Sending voice file {voice_file_path} to OpenAI Whisper API...")

        # Blocking open and transcribe call
        def _transcribe_blocking():
            with open(voice_file_path, "rb") as audio_file_handle: # Renamed to avoid conflict
                # Note: openai.Audio.transcribe might release GIL,
                # but file I/O before it is definitely blocking.
                transcription_result = openai.Audio.transcribe("whisper-1", audio_file_handle)
            return transcription_result.get('text')

        text = await loop.run_in_executor(None, _transcribe_blocking)

        if text is not None: # Check if text is not None, rather than if text is truthy
            log_local_bot_event(f"Voice transcribed successfully: '{text}'")
            return text.strip()
        else:
            log_local_bot_event("Voice transcription returned no text (text is None).")
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
async def handle_voice_message(message):
    """Handles incoming voice messages."""
    chat_id = message.chat.id
    log_local_bot_event(f"Received voice message from {chat_id}. File ID: {message.voice.file_id}")

    if not OPENAI_API_KEY:
        await bot.reply_to(message, "⚠️ Распознавание голоса не настроено на сервере.")
        log_local_bot_event("Voice recognition skipped: OpenAI API key not configured.")
        return

    temp_voice_path = VOICE_FILE_DIR / f"{message.voice.file_id}.ogg" # Define early for finally block

    try:
        file_info = await bot.get_file(message.voice.file_id)
        downloaded_file_bytes = await bot.download_file(file_info.file_path) # download_file returns bytes

        # Save the downloaded file temporarily (blocking I/O)
        import functools
        loop = asyncio.get_event_loop()

        def _save_voice_file():
            with open(temp_voice_path, 'wb') as new_file:
                new_file.write(downloaded_file_bytes)

        await loop.run_in_executor(None, _save_voice_file)
        log_local_bot_event(f"Voice file saved temporarily to {temp_voice_path}")

        transcribed_text = await get_text_from_voice(str(temp_voice_path))

        if transcribed_text is not None: # Process if we have a transcription (even if empty string)
            log_local_bot_event(f"Voice from {chat_id} transcribed to: '{transcribed_text}'")
            await bot.reply_to(message, f"🗣️ Распознано: \"{transcribed_text}\"")
            # Call the unified processor
            await process_user_message(chat_id, transcribed_text, message)
        else: # This means get_text_from_voice returned None (actual error or API key issue)
            await bot.reply_to(message, "Не понял, повтори, пожалуйста. 🎙️")
            log_local_bot_event(f"Transcription failed or returned empty for voice from {chat_id}")

    except Exception as e:
        await bot.reply_to(message, "Произошла ошибка при обработке голосового сообщения. 😥")
        log_local_bot_event(f"Error processing voice message from {chat_id}: {e}")
    finally:
        # Clean up the temporary file (blocking I/O)
        def _check_and_delete_temp_file():
            if temp_voice_path.exists():
                try:
                    os.remove(temp_voice_path)
                    log_local_bot_event(f"Temporary voice file {temp_voice_path} deleted.")
                except OSError as e_os:
                    log_local_bot_event(f"Error deleting temporary voice file {temp_voice_path}: {e_os}")
            else:
                log_local_bot_event(f"Temporary voice file {temp_voice_path} not found for deletion or already deleted.")

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _check_and_delete_temp_file)

# --- GPT Streaming ---
# This functionality is currently bypassed by the KatanaAgent logic.
# If it were to be re-enabled, it would need to be updated to handle async/await properly.

if __name__ == '__main__':
    # asyncio.run(main()) # This was the correct way from previous step
    # Re-ensure main() is called correctly
    async def main_runner():
        log_local_bot_event("Bot starting...")

        # Register commands
        register_command("status", command_status_impl, "Shows the current status of the bot.")
        register_command("help", command_help_impl, "Lists all available commands.")
        register_command("reset", command_reset_impl, "Resets user-specific bot data (e.g., conversation history).")
        # Example of how to unregister, not typically done at startup unless for specific logic
        # unregister_command("some_old_command")

        try:
            await bot.polling(non_stop=True, request_timeout=30)
        except Exception as e:
            log_local_bot_event(f"Bot polling error: {e}")
        finally:
            log_local_bot_event("Bot stopped.")
    asyncio.run(main_runner())




# --- Slash Command Handlers ---

# Note: The @bot.message_handler decorators will still be used by telebot for routing.
# The registration system here is for our internal management (e.g., for /help command).

@trace_command
async def command_status_impl(message):
    """Implementation for the /status command."""
    start_time = datetime.now(timezone.utc)
    chat_id = message.chat.id
    user_id = message.from_user.id
    command_name = "/status"
    status = "error" # Default status
    uptime_str = "N/A"

    log_entry_start = f"command='{command_name}' event_type='start' user_id={user_id} chat_id={chat_id}"
    log_command_event(log_entry_start)

    try:
        uptime_delta = datetime.now(timezone.utc) - BOT_START_TIME
        days = uptime_delta.days
        hours, remainder = divmod(uptime_delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"

        status_message = (
            f"🤖 **Bot Status** 🤖\n\n"
            f"**Uptime:** {uptime_str}\n"
            f"**Version:** 1.0.0 (feat/command-handling-improvements)\n"
            f"**Active Features:** Text, Voice, JSON commands, Slash commands"
        )

        await bot.reply_to(message, status_message, parse_mode="Markdown")
        status = "success"
    except Exception as e:
        error_message = str(e).replace('\n', ' - ') # Sanitize error message for logging
        log_command_event(f"command='{command_name}' event_type='error' user_id={user_id} chat_id={chat_id} error='{error_message}'")
        log_local_bot_event(f"Error processing command {command_name} for user {user_id}: {error_message}")
        await bot.reply_to(message, "An error occurred while fetching status.")
    finally:
        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        log_entry_end = f"command='{command_name}' event_type='end' user_id={user_id} chat_id={chat_id} status='{status}' duration_ms={duration_ms:.2f} details={{'uptime': '{uptime_str}'}}"
        log_command_event(log_entry_end)


@trace_command
async def command_help_impl(message):
    """Implementation for the /help command."""
    start_time = datetime.now(timezone.utc)
    chat_id = message.chat.id
    user_id = message.from_user.id
    command_name = "/help"
    status = "error"

    log_entry_start = f"command='{command_name}' event_type='start' user_id={user_id} chat_id={chat_id}"
    log_command_event(log_entry_start)

    try:
        all_commands = get_all_commands()
        if not all_commands:
            help_text = "No commands are currently registered."
        else:
            help_text = "📚 **Available Commands** 📚\n\n"
            for cmd, desc in sorted(all_commands.items()): # Sort for consistent order
                help_text += f"/{cmd} - {desc}\n"

        await bot.reply_to(message, help_text.strip(), parse_mode="Markdown")
        status = "success"
    except Exception as e:
        error_message = str(e).replace('\n', ' - ')
        log_command_event(f"command='{command_name}' event_type='error' user_id={user_id} chat_id={chat_id} error='{error_message}'")
        log_local_bot_event(f"Error processing command {command_name} for user {user_id}: {error_message}")
        await bot.reply_to(message, "An error occurred while fetching help information.")
    finally:
        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        log_entry_end = f"command='{command_name}' event_type='end' user_id={user_id} chat_id={chat_id} status='{status}' duration_ms={duration_ms:.2f} details={{}}"
        log_command_event(log_entry_end)


@trace_command
async def command_reset_impl(message):
    """Implementation for the /reset command."""
    start_time = datetime.now(timezone.utc)
    chat_id = message.chat.id
    user_id = message.from_user.id
    command_name = "/reset"
    history_cleared_flag = False
    status = "error"

    log_entry_start = f"command='{command_name}' event_type='start' user_id={user_id} chat_id={chat_id}"
    log_command_event(log_entry_start)

    try:
        if chat_id in chat_histories:
            del chat_histories[chat_id]
            response_message = "🧹 Your conversation history with me in this chat has been cleared."
            history_cleared_flag = True
            log_local_bot_event(f"Cleared conversation history for chat_id {chat_id}.")
        else:
            response_message = "🤔 No conversation history found for you in this chat to clear."
            log_local_bot_event(f"No conversation history to clear for chat_id {chat_id}.")

        await bot.reply_to(message, response_message)
        status = "success"
    except Exception as e:
        error_message = str(e).replace('\n', ' - ')
        log_command_event(f"command='{command_name}' event_type='error' user_id={user_id} chat_id={chat_id} error='{error_message}'")
        log_local_bot_event(f"Error processing command {command_name} for user {user_id}: {error_message}")
        await bot.reply_to(message, "An error occurred while resetting history.")
    finally:
        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        log_entry_end = f"command='{command_name}' event_type='end' user_id={user_id} chat_id={chat_id} status='{status}' duration_ms={duration_ms:.2f} details={{'history_cleared': {history_cleared_flag}}}"
        log_command_event(log_entry_end)

# Keep the telebot handlers, but point them to the new _impl functions
@bot.message_handler(commands=['status'])
async def command_status_handler(message):
    await command_status_impl(message)

@bot.message_handler(commands=['help'])
async def command_help_handler(message):
    await command_help_impl(message)

@bot.message_handler(commands=['reset'])
async def command_reset_handler(message):
    await command_reset_impl(message)
