import logging
from telegram import Update
from telegram.ext import ContextTypes
from src.bot.services import get_text_from_voice
import os # Required for file operations

# Configure logging
logger = logging.getLogger(__name__)

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles voice messages, transcribes them, and replies to the user."""
    if not update.message or not update.message.voice:
        logger.warning("handle_voice_message called without a voice message.")
        return

    voice = update.message.voice

    try:
        # Download the voice file
        voice_file_telegram = await voice.get_file()

        # Define a path to save the voice file temporarily
        # In a real bot, you might want a more robust way to handle temporary files
        file_id = voice.file_id
        voice_file_path = f"/tmp/{file_id}.ogg" # Ensure /tmp exists or use a configurable temp dir

        await voice_file_telegram.download_to_drive(voice_file_path)
        logger.info(f"Voice message downloaded to {voice_file_path}")

        # Get text from voice using the service
        transcribed_text = await get_text_from_voice(voice_file_path)

        # Reply to the user
        await update.message.reply_text(transcribed_text)
        logger.info(f"Replied to user with: {transcribed_text}")

    except Exception as e:
        logger.error(f"Error in handle_voice_message: {e}")
        await update.message.reply_text("Произошла ошибка при обработке вашего голосового сообщения.")
    finally:
        # Clean up the downloaded file
        if os.path.exists(voice_file_path):
            try:
                os.remove(voice_file_path)
                logger.info(f"Temporary voice file {voice_file_path} deleted.")
            except OSError as e:
                logger.error(f"Error deleting temporary file {voice_file_path}: {e}")
