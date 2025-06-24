import logging
import os
import json
from datetime import datetime
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment variable for the bot token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Placeholder for a start command, if needed in the future."""
    # This function is not strictly required by the task but good for testing bot responsiveness.
    # await update.message.reply_text("Bot started and listening for messages.")
    logger.info("Bot interaction initiated by user: %s", update.effective_user.id if update.effective_user else "Unknown")


def main() -> None:
    """Start the bot."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set. Exiting.")
        return

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # TODO: Add handlers for text, voice, and documents
    # Define the output file for received messages
    OUTPUT_FILE = "received_messages.log"

    async def _save_message_data(data: dict):
        """Appends message data to the output file in JSON Lines format."""
        try:
            with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            logger.error(f"Error writing to {OUTPUT_FILE}: {e}")

    async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id if update.effective_user else "Unknown"
        chat_id = update.effective_chat.id if update.effective_chat else "Unknown"
        logger.info(f"Received a text message from user {user_id} in chat {chat_id}")

        message_data = {
            "type": "text",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "message_id": update.message.message_id,
            "chat_id": chat_id,
            "user_id": user_id,
            "text": update.message.text,
        }
        await _save_message_data(message_data)

    async def receive_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id if update.effective_user else "Unknown"
        chat_id = update.effective_chat.id if update.effective_chat else "Unknown"
        logger.info(f"Received a voice message from user {user_id} in chat {chat_id}")

        voice = update.message.voice
        message_data = {
            "type": "voice",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "message_id": update.message.message_id,
            "chat_id": chat_id,
            "user_id": user_id,
            "file_id": voice.file_id,
            "file_unique_id": voice.file_unique_id,
            "duration": voice.duration,
            "mime_type": voice.mime_type,
            "file_size": voice.file_size,
        }
        await _save_message_data(message_data)
        # To download the file later:
        # voice_file = await context.bot.get_file(voice.file_id)
        # await voice_file.download_to_drive(f"voice_{voice.file_id}.ogg")

    async def receive_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id if update.effective_user else "Unknown"
        chat_id = update.effective_chat.id if update.effective_chat else "Unknown"
        logger.info(f"Received a document from user {user_id} in chat {chat_id}")

        document = update.message.document
        message_data = {
            "type": "document",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "message_id": update.message.message_id,
            "chat_id": chat_id,
            "user_id": user_id,
            "file_id": document.file_id,
            "file_unique_id": document.file_unique_id,
            "file_name": document.file_name,
            "mime_type": document.mime_type,
            "file_size": document.file_size,
        }
        await _save_message_data(message_data)
        # To download the file later:
        # doc_file = await context.bot.get_file(document.file_id)
        # await doc_file.download_to_drive(document.file_name or f"doc_{document.file_id}")

    # Register handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text))
    application.add_handler(MessageHandler(filters.VOICE, receive_voice))
    application.add_handler(MessageHandler(filters.Document.ALL, receive_document))

    logger.info("Bot started. Listening for updates...")
    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    main()
