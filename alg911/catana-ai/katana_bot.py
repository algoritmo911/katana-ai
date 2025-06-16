import telebot # Ensure this library is installed: pip install pyTelegramBotAPI
import json
import os
from datetime import datetime # Corrected: import datetime object directly
from pathlib import Path # For more robust path handling
from utils.secrets_manager import get_secret

# --- Configuration ---
# Attempt to get token from Google Secret Manager first
GOOGLE_CLOUD_PROJECT = os.getenv('GOOGLE_CLOUD_PROJECT')
TELEGRAM_SECRET_ID = os.getenv('TELEGRAM_SECRET_ID') # e.g., "katana-telegram-bot-token"
API_TOKEN = None

if GOOGLE_CLOUD_PROJECT and TELEGRAM_SECRET_ID:
    print(f"[KatanaBot] GOOGLE_CLOUD_PROJECT and TELEGRAM_SECRET_ID found. Attempting to fetch token...")
    API_TOKEN = get_secret(GOOGLE_CLOUD_PROJECT, TELEGRAM_SECRET_ID)
else:
    print("[KatanaBot] GOOGLE_CLOUD_PROJECT or TELEGRAM_SECRET_ID not set. Falling back to KATANA_TELEGRAM_TOKEN env var.")

if not API_TOKEN: # Fallback if Secret Manager failed or was not configured
    API_TOKEN = os.getenv('KATANA_TELEGRAM_TOKEN', 'YOUR_TELEGRAM_TOKEN') # Original fallback
    if API_TOKEN and API_TOKEN != 'YOUR_TELEGRAM_TOKEN':
        print("[KatanaBot] Loaded API_TOKEN from KATANA_TELEGRAM_TOKEN environment variable.")
    elif not API_TOKEN or API_TOKEN == 'YOUR_TELEGRAM_TOKEN':
        print("[KatanaBot] API_TOKEN not found in Secret Manager or KATANA_TELEGRAM_TOKEN. Loaded placeholder.")
        API_TOKEN = 'YOUR_TELEGRAM_TOKEN'

SCRIPT_DIR = Path(__file__).resolve().parent
COMMANDS_DIR = SCRIPT_DIR / "commands"
STATUS_FILE = SCRIPT_DIR / "status" / "agent_status.json"

# --- Initialize Bot ---
bot = telebot.TeleBot(API_TOKEN)
# Local print logger for the bot
def log_local_bot_event(log_message):
    print(f"[KatanaBot] {datetime.utcnow().isoformat()} - {log_message}")

print("Katana Telegram Bot starting...") # This will print when the script is loaded
log_local_bot_event(f"Commands will be saved to: {COMMANDS_DIR}")
log_local_bot_event(f"Status will be read from: {STATUS_FILE}")

# --- Bot Handlers ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "⚔️ Katana AI Telegram Interface Ready ⚔️\\nSend a JSON command, or use /status or /help.")
    log_local_bot_event(f"Sent welcome message to {message.chat.id}")

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = (
        "Katana AI Bot Help:\\n"
        "- Send a valid JSON string representing a command for the Katana Agent.\\n"
        "  Example module call:\\n"
        "  `{\\"id\\":\\"mycmd001\\", \\"type\\":\\"trigger_module\\", \\"module\\":\\"mind_clearing\\", \\"args\\":{\\"param\\":\\"value\\"}}`\\n"
        "  Example log event:\\n"
        "  `{\\"type\\":\\"log_event\\", \\"message\\":\\"Hello from Telegram Bot\\"}`\\n"
        "- `/status`: Get the last reported status of the Katana Agent.\\n"
        "- `/start`: Display the welcome message.\\n"
        "- `/help`: Display this help message."
    )
    # Using MarkdownV2 requires escaping certain characters in fixed strings if they are present.
    # For this help text, it's mostly fine. If issues, use plain text or selective escaping.
    bot.reply_to(message, help_text, parse_mode="MarkdownV2")
    log_local_bot_event(f"Sent help message to {message.chat.id}")

@bot.message_handler(commands=['status'])
def send_status(message):
    log_local_bot_event(f"Received /status command from {message.chat.id}")
    try:
        if not STATUS_FILE.exists():
            bot.reply_to(message, "⚠️ Agent status file not found. Is the agent running and has it processed a status_check command?")
            log_local_bot_event(f"Status file not found at {STATUS_FILE} when requested by {message.chat.id}")
            return

        with open(STATUS_FILE, "r", encoding="utf-8") as f: # Added encoding
            status_data = json.load(f)

        status_str = json.dumps(status_data, indent=2, ensure_ascii=False)
        # Telegram MarkdownV2 needs specific escaping for some characters within ```json ... ```
        # For simplicity, if status_str contains problematic chars, this might fail.
        # A safer way is to escape `_` `*` `[` `]` `(` `)` `~` `>` `#` `+` `-` `=` `|` `{` `}` `.` `!`
        # For now, assume status_data is simple enough.
        bot.reply_to(message, f"Current Katana Agent Status:\\n```json\\n{status_str}\\n```", parse_mode="MarkdownV2")
        log_local_bot_event(f"Sent status to {message.chat.id}")

    except json.JSONDecodeError:
        bot.reply_to(message, "⚠️ Agent status file is corrupted (not valid JSON).")
        log_local_bot_event(f"Status file {STATUS_FILE} corrupted, requested by {message.chat.id}")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Could not retrieve agent status. Error: {str(e)}")
        log_local_bot_event(f"Error retrieving status for {message.chat.id}: {e}")

@bot.message_handler(func=lambda message: True) # Handles all other messages
def handle_command_json_input(message):
    chat_id = message.chat.id
    log_local_bot_event(f"Received text message from {chat_id}: {message.text}")

    try:
        command_data = json.loads(message.text)

        if not isinstance(command_data, dict):
            bot.reply_to(message, "❌ Invalid command format. Expected a JSON object.")
            log_local_bot_event(f"Invalid command format (not a dict) from {chat_id}: {message.text}")
            return

        command_subdir_name = "telegram_general" # Default if not module-specific
        if command_data.get("type") == "trigger_module" and command_data.get("module"):
            module_name_sanitized = "".join(c if c.isalnum() or c in ['_','-'] else '_' for c in command_data.get("module"))
            if module_name_sanitized:
                 command_subdir_name = f"telegram_mod_{module_name_sanitized}"

        command_file_dir = COMMANDS_DIR / command_subdir_name
        os.makedirs(command_file_dir, exist_ok=True)

        timestamp_str = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f') # Use timezone.utc
        user_identifier = str(chat_id)
        if message.from_user and message.from_user.id:
            user_identifier += f"_{message.from_user.id}"

        file_name_prefix = command_data.get("type", "unknown_type")
        file_name_prefix = "".join(c if c.isalnum() else '_' for c in file_name_prefix)

        command_file_name = f"{file_name_prefix}_{user_identifier}_{timestamp_str}.json"
        command_file_path = command_file_dir / command_file_name

        command_data["_metadata_telegram"] = { # Renamed for clarity
            "source": "telegram_bot",
            "chat_id": chat_id,
            "user_id": message.from_user.id if message.from_user else None,
            "username": message.from_user.username if message.from_user else None,
            "message_id": message.message_id,
            "received_at_bot_utc": datetime.utcnow().isoformat() # Use utcnow for consistency
        }

        with open(command_file_path, "w", encoding="utf-8") as f:
            json.dump(command_data, f, indent=2)

        bot.reply_to(message, f"✅ Command received and saved as {command_subdir_name}/{command_file_name} for Katana Agent processing.")
        log_local_bot_event(f"Command from {chat_id} saved to {command_file_path}")

    except json.JSONDecodeError:
        bot.reply_to(message, "❌ Invalid JSON format. Please send a valid JSON command string. Use /help for examples.")
        log_local_bot_event(f"Invalid JSON from {chat_id}: {message.text}")
    except Exception as e:
        bot.reply_to(message, f"❌ An error occurred while processing your message: {str(e)}")
        log_local_bot_event(f"Error processing message from {chat_id} ('{message.text}'): {e}")

# --- Main ---
if __name__ == '__main__':
    log_local_bot_event("Starting Katana Telegram Bot script execution...")
    if API_TOKEN == 'YOUR_TELEGRAM_TOKEN' or not API_TOKEN: # Check for empty token too
        log_local_bot_event("CRITICAL: API_TOKEN is not set. Please set the KATANA_TELEGRAM_TOKEN environment variable or replace 'YOUR_TELEGRAM_TOKEN' in the script.")
        print("CRITICAL: API_TOKEN is not set for Telegram Bot. Exiting.")
    else:
        log_local_bot_event(f"Bot initialized with token ending: ...{API_TOKEN[-4:] if len(API_TOKEN) > 4 else API_TOKEN}")
        try:
            COMMANDS_DIR.mkdir(parents=True, exist_ok=True)
            STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
            log_local_bot_event("Checked/created necessary directories (commands/, status/).")
        except Exception as e_dir:
            log_local_bot_event(f"Warning: Could not create directories from bot: {e_dir}")

        log_local_bot_event("Starting bot polling loop...")
        try:
            # Added request_timeout for robustness
            bot.polling(none_stop=True, interval=0, request_timeout=30, timeout=20)
        except Exception as e_poll:
            log_local_bot_event(f"CRITICAL_ERROR in bot.polling(): {e_poll}")
            log_local_bot_event("Bot polling stopped due to error.")
