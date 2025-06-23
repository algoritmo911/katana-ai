import telebot.async_telebot # Use AsyncTeleBot
import asyncio # For asyncio operations
import json
import os
from pathlib import Path
from datetime import datetime
import subprocess # Added for run_katana_command
from nlp_mapper import interpret # Added for NLP
import openai # Added for Whisper API
from dotenv import load_dotenv # Added for loading .env file

# Load environment variables from .env file
load_dotenv()

# TODO: Get API token from environment variable or secrets manager
# Using a format-valid dummy token for testing purposes if no env var is set.
API_TOKEN = os.environ.get('TELEGRAM_API_TOKEN', '12345:dummytoken')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

bot = telebot.async_telebot.AsyncTeleBot(API_TOKEN) # Use AsyncTeleBot
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
TELEGRAM_LOG_FILE = LOG_DIR / 'telegram.log'

def log_to_file(message, filename=TELEGRAM_LOG_FILE):
    """Appends a message to the specified log file."""
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.utcnow().isoformat()} | {message}\n")

def log_local_bot_event(message):
    """Logs an event to the console and to the telegram.log file."""
    print(f"[BOT EVENT] {datetime.utcnow().isoformat()}: {message}")
    log_to_file(f"[BOT_EVENT] {message}")

# --- Katana Command Execution ---
async def run_katana_command(command: str) -> str:
    """
    Executes a shell command asynchronously and returns its output.
    This is a simplified placeholder. In a real scenario, this would interact
    with a more complex 'katana_agent' or similar.
    """
    log_local_bot_event(f"Running katana command: {command}")
    try:
        # Using functools.partial to pass arguments to the blocking function
        # when using run_in_executor.
        import functools

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
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
        output = result.stdout.strip()
        if result.stderr.strip():
            output += f"\nStderr:\n{result.stderr.strip()}"
        log_local_bot_event(f"Command output: {output}")
        return output
    except subprocess.CalledProcessError as e:
        error_message = f"Error executing command '{command}': {e.stderr.strip() if e.stderr else 'No stderr'}"
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
        log_to_file(f'[NLU] "{text}" → "{nlp_command}" for chat {chat_id}')
        output = await run_katana_command(nlp_command)
        # Use original_message for reply context if available, otherwise send to chat_id
        reply_target = original_message if original_message else chat_id
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
        command_type = command_data.get("type")

        if command_type == "log_event":
            await handle_log_event(command_data, chat_id)
            await bot.reply_to(original_message, "✅ 'log_event' processed (placeholder).")
            return
        elif command_type == "mind_clearing":
            await handle_mind_clearing(command_data, chat_id)
            await bot.reply_to(original_message, "✅ 'mind_clearing' processed (placeholder).")
            return

        log_local_bot_event(f"Command type '{command_type}' not specifically handled, proceeding with default save. Full command data: {json.dumps(command_data)}")
        try:
            loop = asyncio.get_event_loop()
            timestamp_str = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
            command_file_name = f"{timestamp_str}_{chat_id}.json"
            module_name = command_data.get('module', 'telegram_general')
            module_command_dir_name = f"telegram_mod_{module_name}" if module_name != 'telegram_general' else 'telegram_general'

            def _save_command_file():
                module_command_dir = COMMAND_FILE_DIR / module_command_dir_name
                module_command_dir.mkdir(parents=True, exist_ok=True)
                command_file_path_res = module_command_dir / command_file_name
                with open(command_file_path_res, "w", encoding="utf-8") as f:
                    json.dump(command_data, f, ensure_ascii=False, indent=2)
                return command_file_path_res

            command_file_path = await loop.run_in_executor(None, _save_command_file)
            await bot.reply_to(original_message, f"✅ Command received and saved as `{command_file_path}`.")
            log_local_bot_event(f"Saved command from {chat_id} to {command_file_path}")
        except Exception as e:
            log_local_bot_event(f"Error saving command file for chat {chat_id}: {e}")
            await bot.reply_to(original_message, "⚠️ Error saving command to file.")
        return

    except json.JSONDecodeError:
        # Not NLP, not JSON -> Fallback to GPT
        log_local_bot_event(f"Text from {chat_id} ('{text[:50]}...') is not NLP or JSON. Attempting GPT stream.")
        await bot.send_chat_action(chat_id, 'typing')

        full_response_message = ""
        sent_message_id = None

        async for chunk in get_gpt_streamed_response(text, chat_id):
            full_response_message += chunk
            if not sent_message_id:
                try:
                    # Try to reply to original message if possible, else send new.
                    # GPT responses are not direct replies in terms of quoting, but this keeps context.
                    sent_msg = await bot.reply_to(original_message, full_response_message) if original_message else await bot.send_message(chat_id, full_response_message)
                    sent_message_id = sent_msg.message_id
                    log_local_bot_event(f"GPT stream: Sent initial message {sent_message_id} to chat {chat_id}.")
                except Exception as e:
                    log_local_bot_event(f"Error sending initial GPT message to {chat_id} (attempted reply: {bool(original_message)}): {e}. Sending as new message.")
                    try:
                        sent_msg = await bot.send_message(chat_id, full_response_message)
                        sent_message_id = sent_msg.message_id
                        log_local_bot_event(f"GPT stream: Sent initial message {sent_message_id} (fallback) to chat {chat_id}.")
                    except Exception as e_fallback:
                        log_local_bot_event(f"Error sending fallback initial GPT message to {chat_id}: {e_fallback}")
                        await bot.send_message(chat_id, "⚠️ Error sending GPT response.")
                        return
            else:
                if chunk and sent_message_id:
                    try:
                        await asyncio.sleep(0.1)
                        await bot.edit_message_text(full_response_message, chat_id, sent_message_id)
                        log_local_bot_event(f"GPT stream: Edited message {sent_message_id} in chat {chat_id}.")
                    except telebot.async_telebot.apihelper.ApiTelegramException as e:
                        if "message is not modified" in str(e).lower():
                            log_local_bot_event(f"GPT stream: Message {sent_message_id} not modified, skipping edit.")
                        else:
                            log_local_bot_event(f"Error editing GPT message {sent_message_id} in chat {chat_id}: {e}")
                    except Exception as e:
                        log_local_bot_event(f"General error editing GPT message {sent_message_id} in chat {chat_id}: {e}")

        if not sent_message_id and full_response_message:
             await bot.send_message(chat_id, full_response_message)
        elif not sent_message_id and not full_response_message:
            log_local_bot_event(f"GPT stream for chat {chat_id} resulted in no content to send.")
        return

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
# This mkdir should ideally be at startup, but for now, it's fine.
# If multiple handlers run concurrently before it's created, it might cause issues.
# For simplicity, leaving as is; it has exist_ok=True.
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
            # Create a new message object that looks like a text message
            # This allows reusing the handle_text_message logic
            # Some attributes of message might not be perfectly replicated, but core ones for handle_text_message should be.
            # Important: telebot.types.Message is complex. We only mock what's needed.
            # A cleaner way might be to refactor handle_text_message to accept text directly.
            # For now, this approach minimizes changes to existing text handling.

            # Mimic a text message to pass to handle_text_message - NO LONGER NEEDED
            # We will call process_user_message directly.

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
        # temp_voice_path is defined at the start of the handler's try block
        loop = asyncio.get_event_loop()

        # Check existence and delete in executor to avoid blocking
        # Path.exists() can also be blocking on some systems for network drives, etc.
        # So, we run the check and deletion together in the executor.
        def _check_and_delete_temp_file():
            if temp_voice_path.exists():
                try:
                    os.remove(temp_voice_path)
                    log_local_bot_event(f"Temporary voice file {temp_voice_path} deleted.")
                except OSError as e_os:
                    log_local_bot_event(f"Error deleting temporary voice file {temp_voice_path}: {e_os}")
            else:
                log_local_bot_event(f"Temporary voice file {temp_voice_path} not found for deletion or already deleted.")

        await loop.run_in_executor(None, _check_and_delete_temp_file)

# --- GPT Streaming ---
async def get_gpt_streamed_response(user_text: str, chat_id: int):
    """
    Gets a streamed response from OpenAI GPT asynchronously.
    Yields chunks of text as they are received.
    """
    if not OPENAI_API_KEY:
        log_local_bot_event(f"log_event({chat_id}, \"gpt_skipped_no_api_key\", \"OpenAI API key not configured.\")")
        yield "⚠️ GPT functionality is not configured on the server."
        return

    log_local_bot_event(f"log_event({chat_id}, \"gpt_generation_start\", \"User text: {user_text[:100].replace('\"', 'QUOTE').replacechr(10), '\\n'}...\")")
    try:
        import functools
        loop = asyncio.get_event_loop()

        def _create_openai_stream():
            return openai.ChatCompletion.create(
                model="gpt-3.5-turbo", # Or your preferred model
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": user_text}
                ],
                stream=True
            )

        stream_iterator = await loop.run_in_executor(None, _create_openai_stream)

        _SENTINEL = object()
        while True:
            # Default to None if next fails to avoid StopIteration in executor thread if stream ends abruptly
            chunk_item = await loop.run_in_executor(None, next, stream_iterator, _SENTINEL)

            if chunk_item is _SENTINEL:
                # This debug log can be noisy if streams often end this way.
                # log_local_bot_event(f"log_event({chat_id}, \"gpt_stream_exhausted\", \"Sentinel reached.\")")
                break

            content = chunk_item.choices[0].get("delta", {}).get("content")
            if content:
                # Escape newlines and quotes for cleaner single-line logging
                log_content = content[:50].replace('\n', '\\n').replace('"', 'QUOTE')
                log_local_bot_event(f"log_event({chat_id}, \"gpt_chunk_received\", \"{log_content}...\")")
                yield content

        log_local_bot_event(f"log_event({chat_id}, \"gpt_generation_finished\", \"Stream completed.\")")

    except StopIteration:
        log_local_bot_event(f"log_event({chat_id}, \"gpt_generation_stopped_iteration\", \"StopIteration received, stream likely ended.\")")
    except openai.APIError as e:
        log_local_bot_event(f"log_event({chat_id}, \"gpt_api_error\", \"Error: {str(e).replacechr(10), '\\n'}\")")
        yield f"🤖 GPT Error: {str(e)}"
    except Exception as e:
        log_local_bot_event(f"log_event({chat_id}, \"gpt_unexpected_error\", \"Error: {str(e).replacechr(10), '\\n'}\")")
        yield f"🤖 Unexpected error with GPT: {str(e)}"


if __name__ == '__main__':
    # asyncio.run(main()) # This was the correct way from previous step
    # Re-ensure main() is called correctly
    async def main_runner():
        log_local_bot_event("Bot starting...")
        try:
            await bot.polling(non_stop=True, request_timeout=30)
        except Exception as e:
            log_local_bot_event(f"Bot polling error: {e}")
        finally:
            log_local_bot_event("Bot stopped.")
    asyncio.run(main_runner())
