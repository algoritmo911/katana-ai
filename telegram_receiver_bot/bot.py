import logging
import os
import json
import uuid
from datetime import datetime, timezone
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment variable for the bot token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# --- Katana Integration ---
# Define the path to the katana.commands.json file
# This assumes the telegram_receiver_bot and alg911.catana-ai directories are siblings.
BOT_DIR = os.path.dirname(os.path.abspath(__file__))
COMMANDS_FILE = os.path.join(BOT_DIR, "..", "alg911.catana-ai", "katana.commands.json")


async def _save_command(command_data: dict):
    """
    Reads the command file, appends a new command, and writes it back.
    This is not thread-safe and can lead to race conditions under high load,
    but it is sufficient for this project's expected usage.
    """
    try:
        commands = []
        if os.path.exists(COMMANDS_FILE) and os.path.getsize(COMMANDS_FILE) > 0:
            with open(COMMANDS_FILE, "r", encoding="utf-8") as f:
                try:
                    commands = json.load(f)
                    if not isinstance(commands, list):
                        logger.warning(f"{COMMANDS_FILE} is not a list. Re-initializing.")
                        commands = []
                except json.JSONDecodeError:
                    logger.error(f"Error decoding JSON from {COMMANDS_FILE}. Re-initializing.")
                    commands = []

        commands.append(command_data)

        with open(COMMANDS_FILE, "w", encoding="utf-8") as f:
            json.dump(commands, f, indent=2)

    except Exception as e:
        logger.error(f"Error writing to {COMMANDS_FILE}: {e}")


def _create_command_wrapper(payload: dict) -> dict:
    """Wraps the message payload into a standard command structure."""
    return {
        "command_id": str(uuid.uuid4()),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source": "telegram",
        "command_type": "ingest_message",
        "payload": payload
    }


async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else "Unknown"
    chat_id = update.effective_chat.id if update.effective_chat else "Unknown"
    logger.info(f"Received a text message from user {user_id} in chat {chat_id}")

    payload = {
        "type": "text",
        "message_id": update.message.message_id,
        "chat_id": chat_id,
        "user_id": user_id,
        "text": update.message.text,
    }
    command = _create_command_wrapper(payload)
    await _save_command(command)


async def receive_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else "Unknown"
    chat_id = update.effective_chat.id if update.effective_chat else "Unknown"
    logger.info(f"Received a voice message from user {user_id} in chat {chat_id}")

    voice = update.message.voice
    payload = {
        "type": "voice",
        "message_id": update.message.message_id,
        "chat_id": chat_id,
        "user_id": user_id,
        "file_id": voice.file_id,
        "file_unique_id": voice.file_unique_id,
        "duration": voice.duration,
        "mime_type": voice.mime_type,
        "file_size": voice.file_size,
    }
    command = _create_command_wrapper(payload)
    await _save_command(command)


async def receive_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else "Unknown"
    chat_id = update.effective_chat.id if update.effective_chat else "Unknown"
    logger.info(f"Received a document from user {user_id} in chat {chat_id}")

    document = update.message.document
    payload = {
        "type": "document",
        "message_id": update.message.message_id,
        "chat_id": chat_id,
        "user_id": user_id,
        "file_id": document.file_id,
        "file_unique_id": document.file_unique_id,
        "file_name": document.file_name,
        "mime_type": document.mime_type,
        "file_size": document.file_size,
    }
    command = _create_command_wrapper(payload)
    await _save_command(command)


def main() -> None:
    """Start the bot."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set. Exiting.")
        return

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text))
    application.add_handler(MessageHandler(filters.VOICE, receive_voice))
    application.add_handler(MessageHandler(filters.Document.ALL, receive_document))

    logger.info("Bot started. Listening for updates...")
    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()
