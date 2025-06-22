import telebot
import json
import os
from pathlib import Path
from datetime import datetime, timezone # Added timezone
from typing import Dict, List, Any # For type hinting

# Получаем токен из переменной окружения
API_TOKEN = os.getenv('KATANA_TELEGRAM_TOKEN') # Removed default 'YOUR_API_TOKEN' to make check more explicit
IS_TEST_ENVIRONMENT = os.getenv('PYTEST_CURRENT_TEST') is not None or os.getenv('UNITTEST_RUNNING') is not None

bot = None # Initialize bot as None globally

if not API_TOKEN or ':' not in API_TOKEN:
    if not IS_TEST_ENVIRONMENT:
        raise ValueError("❌ Invalid or missing Telegram API token. Please set KATANA_TELEGRAM_TOKEN env variable with format '123456:ABCDEF' for normal operation.")
    else:
        # In a test environment, we might allow the token to be missing, as 'bot' will be mocked.
        # The dummy token set in test_bot.py's setUpClass will make API_TOKEN valid there.
        # This 'else' branch here handles if even that dummy token isn't set for some reason during test module loading.
        print("INFO: KATANA_TELEGRAM_TOKEN is missing or invalid, but running in a TEST environment. Bot object will be None unless mocked.")
else:
    # Token is present and looks valid, try to initialize if not in a test env
    # where it's expected to be mocked.
    # Note: test_bot.py patches 'bot.katana_bot.bot', so this real instantiation
    # should ideally not run during those tests if the dummy token from setUpClass is respected.
    # However, to be safe, we also check IS_TEST_ENVIRONMENT here.
    if not IS_TEST_ENVIRONMENT:
        try:
            bot = telebot.TeleBot(API_TOKEN)
            print("TeleBot initialized successfully.")
        except Exception as e:
            print(f"Failed to initialize TeleBot with token '{API_TOKEN[:10]}...': {e}. Bot remains None.")
    else:
        # If IS_TEST_ENVIRONMENT is true, even if token is valid (e.g. dummy from test setup),
        # we don't initialize here because tests should control the bot mock.
        print(f"INFO: Valid KATANA_TELEGRAM_TOKEN ('{API_TOKEN[:10]}...') present, but in TEST environment. Real bot not started. Mock is expected.")


# Папка для сохранения команд
COMMAND_FILE_DIR = Path('commands')
COMMAND_FILE_DIR.mkdir(parents=True, exist_ok=True)

# --- Katana State Initialization ---
from .katana_state import KatanaState # Relative import for same package
katana_state = KatanaState()
# --- End Katana State Initialization ---

# --- Backup Configuration ---
BACKUP_DIR = Path("katana_backups")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_INTERVAL_MESSAGES = 100 # Backup every 100 processed messages
message_counter_for_backup = 0
# --- End Backup Configuration ---

def log_local_bot_event(message):
    """Вывод лога события в консоль."""
    print(f"[BOT EVENT] {datetime.utcnow().isoformat()}: {message}")

def handle_log_event(command_data, chat_id):
    """Обработка команды 'log_event' (заглушка)."""
    log_local_bot_event(f"handle_log_event called for chat_id {chat_id} with data: {command_data}")
    # For now, we can log this as a system message in the chat history
    event_details = command_data.get('args', {}).get('details', 'Generic event')
    katana_state.add_chat_message(chat_id, "system_event", f"Event logged: {event_details}")
    # Potentially update global metrics too, if applicable
    # katana_state.update_global_metric(f"last_event_{chat_id}", event_details)


def handle_mind_clearing(command_data, chat_id: str): # Ensure chat_id is consistently str
    """Обработка команды 'mind_clearing'."""
    log_local_bot_event(f"handle_mind_clearing called for chat_id {chat_id} with data: {command_data}")
    katana_state.clear_chat_history(chat_id)
    # The reply text for this will be handled in the main handle_message function after this call.

# --- NLP Provider Integration ---
import openai # Import the openai library
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Placeholder for actual OpenAI client initialization if needed globally
# Example:
# if OPENAI_API_KEY:
#    openai_client = openai.OpenAI(api_key=OPENAI_API_KEY) # New SDK style
# else:
#    openai_client = None

def format_history_for_openai(chat_messages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    formatted_messages = []
    for msg in chat_messages:
        role = "assistant" if msg["sender"] == "katana" else msg["sender"] # user, system_event
        if role not in ["user", "assistant", "system"]: # Filter out system_event or adapt if needed
            if role == "system_event": # Optional: treat system events as system messages or ignore
                # formatted_messages.append({"role": "system", "content": f"System Event: {msg['text']}"})
                continue
            else: # Ignore other unknown roles for now
                continue
        formatted_messages.append({"role": role, "content": msg["text"]})
    return formatted_messages

def get_openai_chat_response(user_prompt: str, history_messages: List[Dict[str, Any]]) -> str:
    if not OPENAI_API_KEY:
        return "🤖 OpenAI API key not configured. Please ask an admin to set it up."

    try:
        # Initialize the client inside the function, or use a global client if preferred and initialized safely
        client = openai.OpenAI(api_key=OPENAI_API_KEY)

        messages_for_api = format_history_for_openai(history_messages)
        messages_for_api.append({"role": "user", "content": user_prompt})

        # Limit history length to avoid overly long requests / high token usage for now
        # e.g., keep last 10 messages (5 user, 5 assistant turns) + system prompt if any
        MAX_HISTORY_MESSAGES_FOR_API = 20 # Keep this configurable or adjust as needed
        if len(messages_for_api) > MAX_HISTORY_MESSAGES_FOR_API:
            messages_for_api = messages_for_api[-MAX_HISTORY_MESSAGES_FOR_API:]


        log_local_bot_event(f"Calling OpenAI with {len(messages_for_api)} messages. Prompt: {user_prompt[:50]}...")

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages_for_api
        )

        ai_response = response.choices[0].message.content
        log_local_bot_event(f"OpenAI response received: {ai_response[:50]}...")
        return ai_response.strip() if ai_response else "🤖 OpenAI returned an empty response."

    except openai.APIConnectionError as e:
        log_local_bot_event(f"OpenAI APIConnectionError: {e}")
        return "🤖 Sorry, I couldn't connect to OpenAI. Please try again later."
    except openai.RateLimitError as e:
        log_local_bot_event(f"OpenAI RateLimitError: {e}")
        return "🤖 I'm a bit overwhelmed with requests to OpenAI right now. Please try again in a moment."
    except openai.APIStatusError as e: # General API error
        log_local_bot_event(f"OpenAI APIStatusError: Status {e.status_code}, Response: {e.response}")
        return f"🤖 Encountered an issue with OpenAI (Status {e.status_code}). Please try again."
    except Exception as e:
        log_local_bot_event(f"An unexpected error occurred while calling OpenAI: {e}")
        return "🤖 An unexpected error occurred while trying to reach OpenAI."


def get_anthropic_chat_response(user_prompt: str, history_messages: List[Dict[str, Any]]) -> str:
    if not ANTHROPIC_API_KEY:
        return "🤖 Anthropic API key not configured. Please ask an admin to set it up."
    # Actual Anthropic API call will be implemented later.
    return (f"🤖 (Placeholder) Would call Anthropic with prompt: {user_prompt} "
            f"(and {len(history_messages)} history messages)")
# --- End NLP Provider Integration ---


def get_katana_response(chat_id: str, command_data: dict, current_raw_history_messages: list) -> str:
    """
    Katana's consciousness. Dispatches to NLP providers or uses internal logic.
    Generates a response based on the command and chat history.
    """
    command_type = command_data.get("type", "unknown_command")
    module = command_data.get("module", "unknown_module") # For dispatching
    args = command_data.get("args", {})
    user_prompt_from_args = args.get("prompt", args.get("text", args.get("query", None))) # Flexible prompt extraction

    # The current_raw_history_messages includes the user's current command/message as the last item.
    # For NLP providers, we want the history *before* this current message.
    history_before_current_prompt = current_raw_history_messages[:-1] if len(current_raw_history_messages) > 0 else []

    if module == "openai_chat" and user_prompt_from_args:
        return get_openai_chat_response(user_prompt_from_args, history_before_current_prompt)
    elif module == "anthropic_chat" and user_prompt_from_args:
        return get_anthropic_chat_response(user_prompt_from_args, history_before_current_prompt)

    # Fallback to existing placeholder logic if no specific NLP module matched or no prompt
    num_past_messages = len(current_raw_history_messages) # Includes the current user message
    if num_past_messages <= 1:
        history_awareness_phrase = "This is our first command message exchange."
    else:
        history_awareness_phrase = f"I see we have {num_past_messages - 1} prior messages in our history."

    fallback_response = (
        f"🤖 Katana Placeholder Response (Fallback):\n"
        f"Received command '{command_type}' for module '{module}'.\n"
        f"{history_awareness_phrase}\n"
        f"I am processing this. My real intelligence is yet to be fully integrated.\n"
        f"Args received: {json.dumps(args)}"
    )
    return fallback_response

# Define handlers, but only register them if bot is initialized
def handle_start_impl(message):
    """Ответ на /start"""
    bot.reply_to(message, "Привет! Я — Katana. Отправь JSON-команду, чтобы начать.")
    log_local_bot_event(f"/start received from {message.chat.id}")

def handle_message_impl(message):
    """Главный обработчик входящих сообщений."""
    global message_counter_for_backup

    chat_id = str(message.chat.id) # Ensure chat_id is a string for KatanaState
    command_text = message.text

    log_local_bot_event(f"Received message from {chat_id}: {command_text}")
    katana_state.add_chat_message(chat_id, "user", command_text)

    # Increment message counter and check for backup trigger BEFORE any early returns
    message_counter_for_backup += 1
    if message_counter_for_backup >= BACKUP_INTERVAL_MESSAGES:
        timestamp_str = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        backup_file_name = f"katana_state_backup_{timestamp_str}.json"
        backup_file_path = BACKUP_DIR / backup_file_name
        log_local_bot_event(f"Message counter reached {message_counter_for_backup}. Triggering backup to {backup_file_path}...")
        katana_state.backup_state(backup_file_path)
        message_counter_for_backup = 0 # Reset counter

    try:
        command_data = json.loads(command_text)
    except json.JSONDecodeError:
        error_reply = "❌ Error: Invalid JSON format. Please send commands in correct JSON."
        if bot: bot.reply_to(message, error_reply) # Check if bot is initialized
        katana_state.add_chat_message(chat_id, "katana", error_reply)
        log_local_bot_event(f"Invalid JSON from {chat_id}: {command_text}")
        return

    # Placeholder for actual Katana consciousness processing
    # For now, we just acknowledge valid JSON commands or specific command types
    # This will be expanded in the "Implement placeholder Katana consciousness" step

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
            katana_state.add_chat_message(chat_id, "katana", error_msg)
            log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text})")
            return
        if field == "id":
            if not any(isinstance(command_data[field], t) for t in expected_type):
                error_msg = f"❌ Error: Field '{field}' must be type str or int. Got {type(command_data[field]).__name__}."
                bot.reply_to(message, error_msg)
                katana_state.add_chat_message(chat_id, "katana", error_msg)
                log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text})")
                return
        elif not isinstance(command_data[field], expected_type):
            error_msg = f"❌ Error: Field '{field}' must be type {expected_type.__name__}. Got {type(command_data[field]).__name__}."
            bot.reply_to(message, error_msg)
            katana_state.add_chat_message(chat_id, "katana", error_msg)
            log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text})")
            return

    command_type = command_data.get("type")

    # This is where Katana's consciousness would process the command_data
    # For now, we'll have specific replies for known command types and a default for others.

    if command_type == "log_event":
        handle_log_event(command_data, chat_id)
        event_details = command_data.get('args', {}).get('details', 'Generic event')
        reply_text = f"✅ Event '{event_details}' logged to my memory for chat {chat_id}."
        bot.reply_to(message, reply_text)
        katana_state.add_chat_message(chat_id, "katana", reply_text)
        return
    elif command_type == "mind_clearing":
        handle_mind_clearing(command_data, chat_id)
        reply_text = f"🧠✨ Katana's mind for chat {chat_id} has been cleared. We start anew."
        bot.reply_to(message, reply_text)
        katana_state.add_chat_message(chat_id, "katana", reply_text)
        return

    # --- Placeholder Katana Consciousness ---
    chat_history_obj = katana_state.get_chat_history(chat_id)
    katana_reply_text = get_katana_response(chat_id, command_data, chat_history_obj.messages)
    bot.reply_to(message, katana_reply_text)
    katana_state.add_chat_message(chat_id, "katana", katana_reply_text)
    log_local_bot_event(f"Command type '{command_type}' processed by placeholder consciousness. Interaction complete.")
    return # Katana has handled it, no need to proceed to file saving reply for this interaction path
    # --- End Placeholder Katana Consciousness ---

    # The following code for saving to file will now only be reached if the above 'return' is not hit.
    # This means specific command types (log_event, mind_clearing) that return early,
    # or future commands that might not use get_katana_response, could still use the file saving if needed,
    # but general commands processed by get_katana_response will not trigger the duplicate "command saved" message.

    log_local_bot_event(f"Command type '{command_type}' not specifically handled by consciousness, proceeding with default save.")
    timestamp_str = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
    command_file_name = f"{timestamp_str}_{chat_id}.json"
    
    module_name = command_data.get('module', 'telegram_general')
    module_command_dir = COMMAND_FILE_DIR / f"telegram_mod_{module_name}" if module_name != 'telegram_general' else COMMAND_FILE_DIR / 'telegram_general'
    module_command_dir.mkdir(parents=True, exist_ok=True)
    command_file_path = module_command_dir / command_file_name

    with open(command_file_path, "w", encoding="utf-8") as f:
        json.dump(command_data, f, ensure_ascii=False, indent=2)
    
    reply_text = f"✅ Command received and saved as `{command_file_path}`."
    bot.reply_to(message, reply_text)
    katana_state.add_chat_message(chat_id, "katana", reply_text)
    log_local_bot_event(f"Saved command from {chat_id} to {command_file_path}")

if bot:
    # Register handlers only if bot is a valid TeleBot instance
    @bot.message_handler(commands=['start'])
    def actual_handle_start(message):
        handle_start_impl(message)

    @bot.message_handler(func=lambda message: True)
    def actual_handle_message(message):
        handle_message_impl(message)

if __name__ == '__main__':
    if bot:
        log_local_bot_event("Bot starting polling...")
        bot.polling()
        log_local_bot_event("Bot polling stopped.")
    else:
        log_local_bot_event("Bot object not initialized. Cannot start polling. Check KATANA_TELEGRAM_TOKEN or test environment setup.")