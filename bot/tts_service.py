import os
import logging
from gtts import gTTS, gTTSError
from pathlib import Path
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ensure a temporary directory for storing TTS files exists
TEMP_AUDIO_DIR = Path(tempfile.gettempdir()) / "katana_tts_cache"
TEMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

class TTSService:
    def __init__(self, default_lang='en'):
        self.default_lang = default_lang

    def text_to_speech(self, text: str, lang: str = None, slow: bool = False) -> str | None:
        """
        Converts text to speech and saves it as an MP3 file.
        Returns the path to the saved audio file, or None if conversion fails.
        """
        current_lang = lang if lang else self.default_lang

        if not text:
            logger.warning("TTS conversion requested for empty text.")
            return None

        try:
            logger.info(f"Requesting TTS for text: '{text[:50]}...' in lang: {current_lang}")
            tts = gTTS(text=text, lang=current_lang, slow=slow)

            # Create a unique temporary filename
            # Using a simple approach here; for high concurrency, consider UUIDs
            temp_file_path = TEMP_AUDIO_DIR / f"tts_output_{os.urandom(4).hex()}.mp3"

            tts.save(str(temp_file_path))
            logger.info(f"TTS audio saved to: {temp_file_path}")
            return str(temp_file_path)

        except gTTSError as e:
            logger.error(f"gTTS Error during TTS conversion for lang {current_lang}: {e}", exc_info=True)
            # Specific gTTS errors could be:
            # - Language not found
            # - Network issue (if gTTS needs to fetch language data)
            # - etc.
            return None
        except Exception as e:
            logger.error(f"Unexpected error during TTS conversion: {e}", exc_info=True)
            return None

    def cleanup_temp_file(self, file_path: str):
        """Deletes a temporary audio file."""
        try:
            if file_path and Path(file_path).exists():
                Path(file_path).unlink()
                logger.info(f"Cleaned up temporary TTS file: {file_path}")
        except Exception as e:
            logger.error(f"Error cleaning up TTS file {file_path}: {e}", exc_info=True)

# Example usage (optional, for testing this module directly)
if __name__ == '__main__':
    tts_service = TTSService()

    text_to_convert = "Hello, this is a test of the text to speech service."
    print(f"\n--- Testing TTS ({tts_service.default_lang}) ---")
    audio_file_path = tts_service.text_to_speech(text_to_convert)

    if audio_file_path:
        print(f"TTS audio file created at: {audio_file_path}")
        # In a real scenario, this file would be sent, then cleaned up.
        # For testing, you might want to manually check the file.
        # tts_service.cleanup_temp_file(audio_file_path) # Example cleanup
    else:
        print("TTS conversion failed.")

    print(f"\n--- Testing TTS (Spanish) ---")
    audio_file_path_es = tts_service.text_to_speech("Hola, esto es una prueba en español.", lang='es')
    if audio_file_path_es:
        print(f"TTS audio file (es) created at: {audio_file_path_es}")
    else:
        print("TTS conversion (es) failed.")

    # Test cleanup
    if audio_file_path:
         tts_service.cleanup_temp_file(audio_file_path)
    if audio_file_path_es:
         tts_service.cleanup_temp_file(audio_file_path_es)
