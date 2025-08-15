import logging
import os
from openai import OpenAI

logger = logging.getLogger(__name__)

client = None
if os.getenv("OPENAI_API_KEY"):
    client = OpenAI()
else:
    logger.warning("OPENAI_API_KEY not found. Transcription will be disabled.")

async def transcribe_audio(audio_file_path: str) -> str | None:
    """
    Transcribes an audio file using the Whisper API.

    :param audio_file_path: The path to the audio file.
    :return: The transcribed text, or None if an error occurs.
    """
    if not client:
        logger.error("OpenAI client not initialized. Cannot transcribe audio.")
        return None

    try:
        with open(audio_file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        logger.info(f"Successfully transcribed audio file {audio_file_path}. Text: '{transcription.text}'")
        return transcription.text
    except Exception as e:
        logger.error(f"Failed to transcribe audio file {audio_file_path}: {e}")
        return None
