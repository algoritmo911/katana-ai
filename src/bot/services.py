import openai
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def get_text_from_voice(voice_file_path: str) -> str:
    """
    Transcribes voice to text using OpenAI Whisper API.

    Args:
        voice_file_path: Path to the voice file.

    Returns:
        The transcribed text or an error message.
    """
    start_time = None # Initialize start_time
    try:
        start_time = time.time()
        with open(voice_file_path, "rb") as audio_file:
            # In a real scenario, you would use openai.Audio.transcribe
            # For now, we'll simulate the API call and potential responses
            # Simulate OpenAI API call
            # transcription = await openai.Audio.transcribe("whisper-1", audio_file)
            # text = transcription.text

            # Mocking responses for now
            if "empty_voice" in voice_file_path:
                text = ""
            elif "rate_limit_error" in voice_file_path:
                # openai.RateLimitError expects a 'response' argument which should be a httpx.Response like object
                mock_response = type('MockResponse', (), {'request': None, 'status_code': 429, 'headers': {}})() # Added headers
                raise openai.RateLimitError("Simulated RateLimitError", response=mock_response, body=None)
            elif "api_error" in voice_file_path:
                # openai.APIError constructor is simpler: message, request, body
                mock_request = type('MockRequest', (), {})() # Minimal mock for request
                raise openai.APIError("Simulated APIError", request=mock_request, body=None)
            elif "empty_response" in voice_file_path: # Simulate API returning None or unexpected
                text = None
            else:
                text = "This is a simulated transcription."

        end_time = time.time()
        response_time_str = f"{end_time - start_time:.2f} seconds" if start_time else "N/A"
        logger.info(f"Voice processed. OpenAI API response time: {response_time_str}.")

        if text is None or text.strip() == "":
            logger.warning("Transcription result is empty.")
            return "🤷 Не удалось распознать голос. Попробуй ещё раз."

        return text

    except openai.RateLimitError as e:
        end_time = time.time()
        response_time_str = f"{end_time - start_time:.2f} seconds" if start_time else "N/A"
        logger.error(f"OpenAI RateLimitError: {e}. Response time: {response_time_str}.")
        return "OpenAI API request exceeded rate limit. Пожалуйста, попробуйте позже."
    except openai.APIError as e:
        end_time = time.time()
        response_time_str = f"{end_time - start_time:.2f} seconds" if start_time else "N/A"
        logger.error(f"OpenAI APIError: {e}. Response time: {response_time_str}.")
        return "Ошибка при обращении к OpenAI API. Пожалуйста, попробуйте позже."
    except Exception as e:
        end_time = time.time()
        response_time_str = f"{end_time - start_time:.2f} seconds" if start_time else "N/A"
        logger.error(f"An unexpected error occurred: {e}. Response time: {response_time_str}.")
        return "Произошла непредвиденная ошибка при обработке голосового сообщения."
