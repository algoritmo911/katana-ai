import logging
import os
import tempfile
from telegram import Update
from .transcriber import transcribe_audio

logger = logging.getLogger(__name__)

async def process_voice_message(update: Update) -> str | None:
    """
    Downloads a voice message, saves it to a temporary file,
    and uses the transcriber to get the text.

    :param update: The Telegram update containing the voice message.
    :return: The transcribed text, or None if an error occurs.
    """
    voice = update.message.voice
    temp_audio_path = None
    try:
        # Create a temporary file path
        fd, temp_audio_path = tempfile.mkstemp(suffix=".ogg")
        os.close(fd) # Close the file descriptor

        voice_file = await voice.get_file()
        await voice_file.download_to_drive(custom_path=temp_audio_path)
        logger.info(f"Voice message downloaded to temporary file: {temp_audio_path}")

        # Transcribe the audio using the shared transcriber module
        transcribed_text = await transcribe_audio(temp_audio_path)

        if transcribed_text is None:
            if update.message:
                await update.message.reply_text("Sorry, I couldn't understand the audio.")
            return None

        return transcribed_text

    except Exception as e:
        logger.error(f"An error occurred during voice processing: {e}")
        if update.message:
            await update.message.reply_text("Sorry, I couldn't process your voice message.")
        return None
    finally:
        # Clean up the temporary file
        if temp_audio_path and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
            logger.info(f"Cleaned up temporary file: {temp_audio_path}")
