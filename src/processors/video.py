import logging
import os
import tempfile
from telegram import Update
from pydub import AudioSegment
from .transcriber import transcribe_audio

logger = logging.getLogger(__name__)

async def process_video_note(update: Update) -> str | None:
    """
    Downloads a video note, extracts audio, transcribes it, and returns the text.

    :param update: The Telegram update containing the video note.
    :return: The transcribed text, or None if an error occurs.
    """
    video_note = update.message.video_note
    temp_video_path = None
    temp_audio_path = None

    try:
        # Create a temporary file path for the video
        fd_video, temp_video_path = tempfile.mkstemp(suffix=".mp4")
        os.close(fd_video)

        # Download the video note
        video_file = await video_note.get_file()
        await video_file.download_to_drive(custom_path=temp_video_path)
        logger.info(f"Video note downloaded to {temp_video_path}")

        # Extract audio from the video
        # This requires ffmpeg to be installed on the system
        audio = AudioSegment.from_file(temp_video_path, format="mp4")

        # Create a temporary file path for the extracted audio
        fd_audio, temp_audio_path = tempfile.mkstemp(suffix=".ogg",)
        os.close(fd_audio)

        # pydub can export to ogg, which works well with Whisper
        audio.export(temp_audio_path, format="ogg", codec="libopus")
        logger.info(f"Extracted audio to {temp_audio_path}")

        # Transcribe the extracted audio
        transcribed_text = await transcribe_audio(temp_audio_path)

        if transcribed_text is None:
            if update.message:
                await update.message.reply_text("Sorry, I couldn't understand the audio from the video.")
            return None

        return transcribed_text

    except FileNotFoundError:
        logger.error("FFmpeg not found. Please ensure it is installed and in your system's PATH.")
        if update.message:
            await update.message.reply_text("Server configuration error: a required audio processing tool (FFmpeg) is missing.")
        return None
    except Exception as e:
        logger.error(f"An error occurred during video note processing: {e}")
        if update.message:
            await update.message.reply_text("Sorry, I couldn't process your video note due to an unexpected error.")
        return None
    finally:
        # Clean up temporary files
        if temp_video_path and os.path.exists(temp_video_path):
            os.remove(temp_video_path)
            logger.info(f"Cleaned up temporary video file: {temp_video_path}")
        if temp_audio_path and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
            logger.info(f"Cleaned up temporary audio file: {temp_audio_path}")
