import telebot.async_telebot # Use AsyncTeleBot
import asyncio # For asyncio operations
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
import subprocess # Added for run_katana_command
from nlp_mapper import interpret # Added for NLP
import openai # Added for Whisper API
from dotenv import load_dotenv # Added for loading .env file
from katana_memory.memory_api import MemoryManager # Added for Katana Memory
import distiller # For conversation distillation

# Load environment variables from .env file
load_dotenv()

# TODO: Get API token from environment variable or secrets manager
# Using a format-valid dummy token for testing purposes if no env var is set.
API_TOKEN = os.environ.get('TELEGRAM_API_TOKEN', '12345:dummytoken')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

bot = telebot.async_telebot.AsyncTeleBot(API_TOKEN) # Use AsyncTeleBot
memory_manager = MemoryManager() # Initialize MemoryManager

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

# Dictionary to store active GPT streaming tasks and their cancellation events
active_gpt_streams = {}

# --- Mnemosyne Protocol: Long-Term Memory ---
# Global state for tracking user activity for the distiller
user_last_message_time = {}
active_chat_ids = set()
DISTILLATION_INACTIVITY_THRESHOLD = timedelta(minutes=15)
DISTILLATION_CHECK_INTERVAL_SECONDS = 300 # 5 minutes

async def conversation_distillation_worker():
    """
    A background worker that periodically checks for inactive conversations
    and triggers the distillation process to store them in long-term memory.
    """
    log_local_bot_event("Mnemosyne Protocol: Conversation distillation worker started.")
    while True:
        await asyncio.sleep(DISTILLATION_CHECK_INTERVAL_SECONDS)
        log_local_bot_event("[DISTILLER WORKER] Running periodic check for inactive conversations.")

        now = datetime.utcnow()
        # Iterate over a copy of the set as we might modify it
        inactive_chats = {
            chat_id for chat_id in active_chat_ids
            if now - user_last_message_time.get(chat_id, now) > DISTILLATION_INACTIVITY_THRESHOLD
        }

        for chat_id in inactive_chats:
            log_local_bot_event(f"[DISTILLER WORKER] Chat {chat_id} is inactive. Starting distillation process.")

            try:
                # 1. Recall conversation from short-term memory
                conversation_history = await memory_manager.recall(chat_id)
                if not conversation_history or len(conversation_history.splitlines()) < 2: # Don't distill single-line chats
                    log_local_bot_event(f"[DISTILLER WORKER] Conversation for {chat_id} is too short or empty. Clearing memory without distillation.")
                    await memory_manager.forget(chat_id)
                    # Remove from activity tracking
                    active_chat_ids.remove(chat_id)
                    if chat_id in user_last_message_time:
                        del user_last_message_time[chat_id]
                    continue

                # 2. Distill and embed the conversation
                distillation_result = await distiller.distill_and_embed_conversation(conversation_history)

                if distillation_result:
                    summary, embedding = distillation_result
                    # 3. Store in long-term memory (Neurovault)
                    metadata = {"chat_id": chat_id, "distilled_at": now.isoformat()}
                    await memory_manager.store_long_term(summary, embedding, metadata)
                    log_local_bot_event(f"[DISTILLER WORKER] Successfully stored distilled memory for chat {chat_id}.")
                else:
                    log_local_bot_event(f"[DISTILLER WORKER] Distillation failed or returned no result for chat {chat_id}. Memory will not be stored.")

                # 4. Forget the short-term memory to prevent reprocessing
                await memory_manager.forget(chat_id)
                log_local_bot_event(f"[DISTILLER WORKER] Cleared short-term memory for chat {chat_id}.")

                # 5. Remove from activity tracking
                active_chat_ids.remove(chat_id)
                if chat_id in user_last_message_time:
                    del user_last_message_time[chat_id]
                log_local_bot_event(f"[DISTILLER WORKER] Finished processing for chat {chat_id}.")

            except Exception as e:
                log_local_bot_event(f"[DISTILLER WORKER] Error processing chat {chat_id}: {e}")

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
    """Handles 'mind_clearing' commands by forgetting conversation history."""
    log_local_bot_event(f"handle_mind_clearing called for chat_id {chat_id} with data: {json.dumps(command_data)}")
    try:
        await memory_manager.forget(chat_id)
        log_local_bot_event(f"Successfully cleared memory for chat_id {chat_id}.")
        # It's good practice to inform the user, but this function doesn't have `original_message`
        # The reply is handled by the caller in `process_user_message`
    except Exception as e:
        log_local_bot_event(f"Error clearing memory for chat_id {chat_id}: {e}")
        # Similar to above, error reporting to user should be handled by caller if needed.
    # await bot.reply_to(message, "✅ 'mind_clearing' received (placeholder).") # Reply handled by `process_user_message`

# --- Unified Message Processing ---
async def process_user_message(chat_id: int, text: str, original_message: telebot.types.Message):
    """
    Processes user text, whether from a direct text message or transcribed voice.
    Handles NLP, JSON commands, or falls back to GPT.
    """
    log_local_bot_event(f"Processing user message for chat {chat_id}: '{text[:100]}...'")

    # Mnemosyne Protocol: Update activity trackers
    user_last_message_time[chat_id] = datetime.utcnow()
    active_chat_ids.add(chat_id)

    # Remember the user's message
    # We store the new message before retrieving history to include it in the current context if immediately needed.
    # However, for GPT context, history is usually retrieved *before* adding the current message to the prompt.
    # Let's store it first, and GPT context retrieval can decide how to use it.
    try:
        await memory_manager.remember(chat_id, f"User: {text}")
        log_local_bot_event(f"Message from chat {chat_id} stored in short-term memory.")
    except Exception as e:
        log_local_bot_event(f"Error remembering message for chat {chat_id}: {e}")

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
        log_local_bot_event(f"Text from {chat_id} ('{text[:50]}...') is not NLP or JSON. Attempting GPT stream with long-term memory recall.")

        # --- Mnemosyne Protocol: Recall relevant memories ---
        long_term_context = ""
        try:
            # 1. Create an embedding for the user's current message
            query_embedding = await _get_embedding(text)
            if query_embedding:
                # 2. Find related memories
                related_memories = await memory_manager.recall_long_term(query_embedding)
                if related_memories:
                    # 3. Format memories for the prompt
                    formatted_memories = [f"- {mem['content']} (similarity: {mem['similarity']:.2f})" for mem in related_memories]
                    long_term_context = "\n".join(formatted_memories)
                    log_local_bot_event(f"Found {len(related_memories)} relevant long-term memories for chat {chat_id}.")
        except Exception as e:
            log_local_bot_event(f"Error during long-term memory recall for chat {chat_id}: {e}")
        # --- End of Recall ---

        if chat_id in active_gpt_streams:
            old_task, old_cancel_event, old_msg_id = active_gpt_streams[chat_id]
            log_local_bot_event(f"log_event({chat_id}, \"gpt_interrupt_request\", \"New message received, attempting to cancel previous stream for message {old_msg_id}.\")")
            old_cancel_event.set()
            try:
                await asyncio.wait_for(old_task, timeout=2.0)
            except asyncio.TimeoutError:
                log_local_bot_event(f"log_event({chat_id}, \"gpt_previous_stream_timeout\", \"Timeout waiting for previous stream task for message {old_msg_id} to cancel.\")")

        async def _handle_gpt_streaming_for_chat(current_text, current_chat_id, current_original_message, current_cancellation_event, long_term_context_str=""):
            sent_message_id = None
            full_response_message = ""
            try:
                await bot.send_chat_action(current_chat_id, 'typing')

                # Pass the long-term context to the response generator
                async for chunk in get_gpt_streamed_response(current_text, current_chat_id, current_cancellation_event, long_term_context=long_term_context_str):
                    if current_cancellation_event.is_set():
                        log_local_bot_event(f"log_event({current_chat_id}, \"gpt_streaming_loop_cancelled\", \"Cancellation detected in process_user_message loop.\")")
                        break
                    full_response_message += chunk
                    if not sent_message_id:
                        try:
                            sent_msg = await bot.reply_to(current_original_message, full_response_message) if current_original_message else await bot.send_message(current_chat_id, full_response_message)
                            sent_message_id = sent_msg.message_id
                            # Store/update message_id in active_gpt_streams if needed, though it's tricky with task structure
                            # For now, the initial message_id is what we might care about for context if we re-implement cancellation details
                            if current_chat_id in active_gpt_streams: # Update message_id if task is still current
                                task, cancel_event, _ = active_gpt_streams[current_chat_id]
                                active_gpt_streams[current_chat_id] = (task, cancel_event, sent_message_id)

                            log_local_bot_event(f"GPT stream: Sent initial message {sent_message_id} to chat {current_chat_id}.")
                        except Exception as e_send:
                            log_local_bot_event(f"Error sending initial GPT message to {current_chat_id}: {e_send}. Sending as new message.")
                            try:
                                sent_msg = await bot.send_message(current_chat_id, full_response_message)
                                sent_message_id = sent_msg.message_id
                                if current_chat_id in active_gpt_streams: # Update message_id
                                   task, cancel_event, _ = active_gpt_streams[current_chat_id]
                                   active_gpt_streams[current_chat_id] = (task, cancel_event, sent_message_id)
                                log_local_bot_event(f"GPT stream: Sent initial message {sent_message_id} (fallback) to chat {current_chat_id}.")
                            except Exception as e_fallback:
                                log_local_bot_event(f"Error sending fallback initial GPT message to {current_chat_id}: {e_fallback}")
                                await bot.send_message(current_chat_id, "⚠️ Error sending GPT response.")
                                return # Exit this specific handler coroutine
                    else:
                        if chunk and sent_message_id: # Ensure there's new content and a message to edit
                            try:
                                await asyncio.sleep(0.1) # Keep small delay
                                await bot.edit_message_text(full_response_message, current_chat_id, sent_message_id)
                                log_local_bot_event(f"GPT stream: Edited message {sent_message_id} in chat {current_chat_id}.")
                            except telebot.async_telebot.apihelper.ApiTelegramException as e_edit:
                                if "message is not modified" in str(e_edit).lower():
                                    log_local_bot_event(f"GPT stream: Message {sent_message_id} not modified, skipping edit.")
                                elif "message to edit not found" in str(e_edit).lower() or "message can't be edited" in str(e_edit).lower() :
                                    log_local_bot_event(f"GPT stream: Message {sent_message_id} not found or can't be edited. Stopping edits for this stream. Error: {e_edit}")
                                    break # Stop trying to edit this message
                                else:
                                    log_local_bot_event(f"Error editing GPT message {sent_message_id} in chat {current_chat_id}: {e_edit}")
                            except Exception as e_gen_edit:
                                log_local_bot_event(f"General error editing GPT message {sent_message_id} in chat {current_chat_id}: {e_gen_edit}")

                if not sent_message_id and full_response_message and not current_cancellation_event.is_set():
                     await bot.send_message(current_chat_id, full_response_message)
                elif not sent_message_id and not full_response_message:
                    log_local_bot_event(f"GPT stream for chat {current_chat_id} resulted in no content to send.")

            except asyncio.CancelledError:
                log_local_bot_event(f"log_event({current_chat_id}, \"gpt_streaming_task_cancelled\", \"Task for GPT streaming was cancelled externally.\")")
                # Potentially send a message like "Previous response generation cancelled." - but might be noisy
            except Exception as e_outer:
                log_local_bot_event(f"log_event({current_chat_id}, \"gpt_streaming_task_error\", \"Error in GPT streaming task: {e_outer}\")")
                if sent_message_id and not full_response_message: # Error before any content, or message was deleted
                    pass # Avoid sending generic error if we couldn't even start
                elif not current_cancellation_event.is_set(): # Don't send error if it was cancelled.
                    try:
                        await bot.send_message(current_chat_id, "⚠️ An error occurred while generating the response.")
                    except Exception:
                        pass # Best effort
            finally:
                log_local_bot_event(f"log_event({current_chat_id}, \"gpt_streaming_task_finally\", \"Finishing GPT task. Sent message ID: {sent_message_id}\")")
                # Remove this task from active streams
                if active_gpt_streams.get(current_chat_id) and active_gpt_streams[current_chat_id][0] is asyncio.current_task():
                    del active_gpt_streams[current_chat_id]
                    log_local_bot_event(f"log_event({current_chat_id}, \"gpt_active_stream_removed\", \"Task removed from active streams.\")")
                else:
                    # This might happen if a new task rapidly replaced this one due to quick succession of messages
                    log_local_bot_event(f"log_event({current_chat_id}, \"gpt_active_stream_mismatch_on_remove\", \"Task not found or already replaced in active streams during cleanup.\")")


        # Create and store the new task
        new_cancellation_event = asyncio.Event()
        # Pass the long-term context to the handler
        gpt_task = asyncio.create_task(
            _handle_gpt_streaming_for_chat(text, chat_id, original_message, new_cancellation_event, long_term_context_str=long_term_context)
        )
        active_gpt_streams[chat_id] = (gpt_task, new_cancellation_event, None)
        log_local_bot_event(f"log_event({chat_id}, \"gpt_new_stream_task_created\", \"New GPT stream task started.\")")
        # Note: We don't await gpt_task here, it runs in the background.
        return
        # --- End of new task management ---

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

# --- Embedding Helper ---
async def _get_embedding(text: str, model="text-embedding-ada-002"):
    """Helper function to create an embedding for a given text."""
    if not OPENAI_API_KEY:
        return None
    try:
        # Use asyncio.to_thread for the blocking OpenAI SDK call
        response = await asyncio.to_thread(
            openai.Embedding.create,
            input=[text],
            model=model
        )
        return response['data'][0]['embedding']
    except Exception as e:
        log_local_bot_event(f"Error creating embedding: {e}")
        return None

# --- GPT Streaming ---
async def get_gpt_streamed_response(user_text: str, chat_id: int, cancellation_event: asyncio.Event, long_term_context: str = ""):
    """
    Gets a streamed response from OpenAI GPT asynchronously, including long-term context.
    Yields chunks of text as they are received.
    Stops if cancellation_event is set.
    """
    if not OPENAI_API_KEY:
        log_local_bot_event(f"log_event({chat_id}, \"gpt_skipped_no_api_key\", \"OpenAI API key not configured.\")")
        yield "⚠️ GPT functionality is not configured on the server."
        return

    # 1. Retrieve short-term conversation history
    short_term_history = ""
    try:
        recalled_history = await memory_manager.recall(chat_id)
        if recalled_history:
            short_term_history = f"PREVIOUS CONVERSATION (Short-Term):\n{recalled_history}\n\n---\n"
            log_local_bot_event(f"Retrieved short-term history for chat {chat_id} for GPT context.")
    except Exception as e:
        log_local_bot_event(f"Error retrieving short-term history for chat {chat_id}: {e}")

    # 2. Construct the final prompt with all context
    system_prompt = "You are a helpful assistant. Use the provided context to inform your answers."

    context_prompt_part = ""
    if long_term_context:
        context_prompt_part += f"RELEVANT MEMORIES (Long-Term):\n{long_term_context}\n\n---\n"

    full_user_prompt = f"{context_prompt_part}{short_term_history}CURRENT USER MESSAGE: {user_text}"

    log_local_bot_event(f"log_event({chat_id}, \"gpt_generation_start\", \"User text (with context): {full_user_prompt[:300].replace('\"', 'QUOTE').replace('\n', '\\n')}...\")")
    try:
        import functools
        loop = asyncio.get_event_loop()

        if cancellation_event.is_set():
            log_local_bot_event(f"log_event({chat_id}, \"gpt_generation_cancelled_before_start\", \"Cancellation event set before API call.\")")
            return

        def _create_openai_stream():
            messages_for_gpt = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_user_prompt}
            ]

            return openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages_for_gpt,
                stream=True
            )

        stream_iterator = await loop.run_in_executor(None, _create_openai_stream)

        _SENTINEL = object()
        full_gpt_response = ""
        while True:
            if cancellation_event.is_set():
                log_local_bot_event(f"log_event({chat_id}, \"gpt_generation_cancelled_pre_chunk_fetch\", \"Cancellation event set before fetching next chunk.\")")
                break

            chunk_item = await loop.run_in_executor(None, next, stream_iterator, _SENTINEL)

            if cancellation_event.is_set(): # Check again immediately after the blocking call returns
                log_local_bot_event(f"log_event({chat_id}, \"gpt_generation_cancelled_post_chunk_fetch\", \"Cancellation event set after fetching chunk.\")")
                break

            if chunk_item is _SENTINEL:
                break

            content = chunk_item.choices[0].get("delta", {}).get("content")
            if content:
                log_content = content[:50].replace('\n', '\\n').replace('"', 'QUOTE')
                log_local_bot_event(f"log_event({chat_id}, \"gpt_chunk_received\", \"{log_content}...\")")
                full_gpt_response += content
                yield content

        if full_gpt_response and not cancellation_event.is_set():
            try:
                await memory_manager.remember(chat_id, f"Assistant: {full_gpt_response}")
                log_local_bot_event(f"GPT response for chat {chat_id} stored in short-term memory.")
            except Exception as e:
                log_local_bot_event(f"Error remembering GPT response for chat {chat_id}: {e}")


        if not cancellation_event.is_set(): # Only log 'finished' if not cancelled
            log_local_bot_event(f"log_event({chat_id}, \"gpt_generation_finished\", \"Stream completed naturally.\")")
        else:
            log_local_bot_event(f"log_event({chat_id}, \"gpt_generation_ended_by_cancellation\", \"Stream processing stopped due to cancellation.\")")


    except StopIteration:
        # This block might be redundant if full_gpt_response is handled correctly after the loop
        if full_gpt_response and not cancellation_event.is_set(): # Check if response was already stored
            # This logic is mostly covered by the post-loop storage.
            # However, if StopIteration happens abruptly, this might catch it.
            # Ensure no double storage. The current logic seems to favor post-loop storage.
            pass
        if not cancellation_event.is_set(): # Avoid double logging if cancellation happened near end
            log_local_bot_event(f"log_event({chat_id}, \"gpt_generation_stopped_iteration\", \"StopIteration received, stream likely ended.\")")
    except openai.APIError as e:
        log_local_bot_event(f"log_event({chat_id}, \"gpt_api_error\", \"Error: {str(e).replace('\n', '\\n')}\")")
        if not cancellation_event.is_set(): # Don't yield error if cancelled, it's not relevant to user
            yield f"🤖 GPT Error: {str(e)}"
    except Exception as e:
        log_local_bot_event(f"log_event({chat_id}, \"gpt_unexpected_error\", \"Error: {str(e).replace('\n', '\\n')}\")")
        if not cancellation_event.is_set():
            yield f"🤖 Unexpected error with GPT: {str(e)}"


if __name__ == '__main__':
    async def main_runner():
        log_local_bot_event("Bot starting...")

        # Start the Mnemosyne Protocol worker
        distillation_task = asyncio.create_task(conversation_distillation_worker())

        try:
            await bot.polling(non_stop=True, request_timeout=30)
        except Exception as e:
            log_local_bot_event(f"Bot polling error: {e}")
        finally:
            log_local_bot_event("Bot stopping...")

            # Gracefully shut down the distillation worker
            distillation_task.cancel()
            try:
                await distillation_task
            except asyncio.CancelledError:
                log_local_bot_event("Distillation worker cancelled successfully.")

            if memory_manager:
                try:
                    log_local_bot_event("Closing MemoryManager connections...")
                    await memory_manager.close_connections()
                    log_local_bot_event("MemoryManager connections closed.")
                except Exception as e_mem:
                    log_local_bot_event(f"Error closing MemoryManager connections: {e_mem}")

            log_local_bot_event("Bot stopped.")

    asyncio.run(main_runner())
