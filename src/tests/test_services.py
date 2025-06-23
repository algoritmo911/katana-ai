import pytest
import openai # Required for the errors
from unittest.mock import patch, mock_open
from src.bot.services import get_text_from_voice
import logging # For caplog.set_level
import time # For time.time() in mock side_effect

@pytest.mark.asyncio
async def test_get_text_from_voice_successful_transcription():
    """Test successful transcription."""
    with patch("builtins.open", mock_open(read_data=b"fake_audio_data")):
        text = await get_text_from_voice("fake_path/normal_audio.ogg")
        assert text == "This is a simulated transcription."

@pytest.mark.asyncio
async def test_get_text_from_voice_empty_voice_input():
    """Test the fallback message for empty voice input (empty string from Whisper)."""
    with patch("builtins.open", mock_open(read_data=b"fake_audio_data")):
        text = await get_text_from_voice("fake_path/empty_voice.ogg")
        assert text == "🤷 Не удалось распознать голос. Попробуй ещё раз."

@pytest.mark.asyncio
async def test_get_text_from_voice_openai_rate_limit_error():
    """Test RateLimitError handling."""
    with patch("builtins.open", mock_open(read_data=b"fake_audio_data")):
        text = await get_text_from_voice("fake_path/rate_limit_error.ogg")
        assert text == "OpenAI API request exceeded rate limit. Пожалуйста, попробуйте позже."

@pytest.mark.asyncio
async def test_get_text_from_voice_openai_api_error():
    """Test APIError handling."""
    with patch("builtins.open", mock_open(read_data=b"fake_audio_data")):
        text = await get_text_from_voice("fake_path/api_error.ogg")
        assert text == "Ошибка при обращении к OpenAI API. Пожалуйста, попробуйте позже."

@pytest.mark.asyncio
async def test_get_text_from_voice_openai_empty_response():
    """Test handling of an empty or None response from OpenAI API."""
    with patch("builtins.open", mock_open(read_data=b"fake_audio_data")):
        text = await get_text_from_voice("fake_path/empty_response.ogg")
        assert text == "🤷 Не удалось распознать голос. Попробуй ещё раз."

@pytest.mark.asyncio
async def test_get_text_from_voice_unexpected_error():
    """Test handling of an unexpected error during the process."""
    with patch("builtins.open", mock_open(read_data=b"fake_audio_data")):
        with patch("src.bot.services.time") as mock_time_module: # Patch time module used by services
            # First call (for start_time) raises Exception, subsequent calls (for end_time) return a value
            mock_time_module.time.side_effect = [Exception("Unexpected file processing error"), time.time()]
            text = await get_text_from_voice("fake_path/any_audio.ogg")
            assert text == "Произошла непредвиденная ошибка при обработке голосового сообщения."

@pytest.mark.asyncio
async def test_get_text_from_voice_logging(caplog):
    """Test that requests and responses are logged."""
    # Ensure the logger messages can be captured by caplog
    logger_under_test = logging.getLogger("src.bot.services")
    logger_under_test.propagate = True
    # Caplog captures from the root logger by default if a specific logger isn't working
    # or from the specified logger if it has a handler caplog can use.
    # Pytest's caplog fixture adds a handler to the logger being watched.
    # Let's ensure the logger itself has a level that allows messages through.
    logger_under_test.setLevel(logging.DEBUG) # Set level on the logger itself

    caplog.set_level(logging.DEBUG) # Set level for caplog's handler too

    # Ensure time.time() works as expected within this test's scope for logging response times
    with patch("builtins.open", mock_open(read_data=b"fake_audio_data")), \
         patch("src.bot.services.time") as mock_time_module:
        mock_time_module.time.side_effect = [1.0, 2.0] # Mock start_time, end_time
        await get_text_from_voice("fake_path/logging_test.ogg")
        assert "Voice processed." in caplog.text
        assert "OpenAI API response time: 1.00 seconds" in caplog.text # Be more specific

    caplog.clear()
    with patch("builtins.open", mock_open(read_data=b"fake_audio_data")), \
         patch("src.bot.services.time") as mock_time_module:
        mock_time_module.time.side_effect = [10.0, 11.0] # Different mock times
        await get_text_from_voice("fake_path/rate_limit_error.ogg")
        assert "OpenAI RateLimitError" in caplog.text
        assert "Response time: 1.00 seconds" in caplog.text

    caplog.clear()
    with patch("builtins.open", mock_open(read_data=b"fake_audio_data")), \
         patch("src.bot.services.time") as mock_time_module:
        mock_time_module.time.side_effect = [12.0, 13.0]
        await get_text_from_voice("fake_path/api_error.ogg")
        assert "OpenAI APIError" in caplog.text
        assert "Response time: 1.00 seconds" in caplog.text

    caplog.clear()
    with patch("builtins.open", mock_open(read_data=b"fake_audio_data")), \
         patch("src.bot.services.time") as mock_time_module:
        mock_time_module.time.side_effect = [14.0, 15.0]
        await get_text_from_voice("fake_path/empty_voice.ogg")
        assert "Transcription result is empty." in caplog.text
        assert "OpenAI API response time: 1.00 seconds" in caplog.text

    caplog.clear()
    # Test unexpected error logging
    with patch("builtins.open", mock_open(read_data=b"fake_audio_data")), \
         patch("src.bot.services.time") as mock_time_module: # Correctly patch src.bot.services.time
        # First call to time.time() (start_time) raises, second call (end_time in except) returns a value
        mock_time_module.time.side_effect = [Exception("Logging unexpected error"), time.time()]
        await get_text_from_voice("fake_path/unexpected_for_log.ogg")
        assert "An unexpected error occurred: Logging unexpected error" in caplog.text # This is an ERROR
        assert "Response time: N/A" in caplog.text # Check for N/A as start_time failed
