import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from telegram import Update, Message, Voice, File
from telegram.ext import ContextTypes
from src.bot.handlers import handle_voice_message
import os

@pytest.fixture
def mock_update_voice():
    """Fixture to create a mock Update object with a voice message."""
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.voice = MagicMock(spec=Voice)
    update.message.voice.file_id = "test_file_id"

    # Mock the file object that get_file() would return
    mock_file_telegram = AsyncMock(spec=File)
    mock_file_telegram.file_path = "http://example.com/file_path.ogg" # Dummy path
    # mock_file_telegram.download.return_value = "test_file_id.ogg" # Simulate download path
    mock_file_telegram.download_to_drive = AsyncMock(return_value=None) # Simulate download

    update.message.voice.get_file = AsyncMock(return_value=mock_file_telegram)
    update.message.reply_text = AsyncMock()
    return update

@pytest.fixture
def mock_context():
    """Fixture to create a mock ContextTypes object."""
    return MagicMock(spec=ContextTypes.DEFAULT_TYPE)

@pytest.mark.asyncio
@patch('src.bot.handlers.get_text_from_voice', new_callable=AsyncMock)
@patch('src.bot.handlers.os.path.exists')
@patch('src.bot.handlers.os.remove')
async def test_handle_voice_message_success(mock_os_remove, mock_os_exists, mock_get_text, mock_update_voice, mock_context):
    """Test successful handling of a voice message."""
    mock_get_text.return_value = "Hello, this is a test."
    mock_os_exists.return_value = True # Assume file exists for cleanup

    await handle_voice_message(mock_update_voice, mock_context)

    # Check that get_file was called
    mock_update_voice.message.voice.get_file.assert_called_once()

    # Check that download_to_drive was called (or download, depending on implementation)
    # The path used for download should match what's in handle_voice_message
    expected_download_path = "/tmp/test_file_id.ogg"
    mock_update_voice.message.voice.get_file.return_value.download_to_drive.assert_called_once_with(expected_download_path)

    # Check that get_text_from_voice was called with the correct path
    mock_get_text.assert_called_once_with(expected_download_path)

    # Check that reply_text was called with the result
    mock_update_voice.message.reply_text.assert_called_once_with("Hello, this is a test.")

    # Check that file cleanup was attempted
    mock_os_exists.assert_called_once_with(expected_download_path)
    mock_os_remove.assert_called_once_with(expected_download_path)

@pytest.mark.asyncio
@patch('src.bot.handlers.get_text_from_voice', new_callable=AsyncMock)
@patch('src.bot.handlers.os.path.exists')
@patch('src.bot.handlers.os.remove')
async def test_handle_voice_message_empty_transcription(mock_os_remove, mock_os_exists, mock_get_text, mock_update_voice, mock_context):
    """Test handling when transcription is empty (e.g., "Не удалось распознать")."""
    mock_get_text.return_value = "🤷 Не удалось распознать голос. Попробуй ещё раз."
    mock_os_exists.return_value = True

    await handle_voice_message(mock_update_voice, mock_context)

    mock_get_text.assert_called_once()
    mock_update_voice.message.reply_text.assert_called_once_with("🤷 Не удалось распознать голос. Попробуй ещё раз.")
    mock_os_remove.assert_called_once()

@pytest.mark.asyncio
@patch('src.bot.handlers.get_text_from_voice', new_callable=AsyncMock)
@patch('src.bot.handlers.os.path.exists')
@patch('src.bot.handlers.os.remove')
async def test_handle_voice_message_openai_error(mock_os_remove, mock_os_exists, mock_get_text, mock_update_voice, mock_context):
    """Test handling when get_text_from_voice returns an OpenAI error message."""
    mock_get_text.return_value = "OpenAI API request exceeded rate limit. Пожалуйста, попробуйте позже."
    mock_os_exists.return_value = True

    await handle_voice_message(mock_update_voice, mock_context)

    mock_get_text.assert_called_once()
    mock_update_voice.message.reply_text.assert_called_once_with("OpenAI API request exceeded rate limit. Пожалуйста, попробуйте позже.")
    mock_os_remove.assert_called_once()

@pytest.mark.asyncio
@patch('src.bot.handlers.get_text_from_voice', new_callable=AsyncMock)
async def test_handle_voice_message_download_exception(mock_get_text, mock_update_voice, mock_context):
    """Test handling when an exception occurs during voice file download."""
    # Simulate an error during the download process
    mock_update_voice.message.voice.get_file.return_value.download_to_drive.side_effect = Exception("Download failed")

    await handle_voice_message(mock_update_voice, mock_context)

    # Ensure get_text_from_voice was not called
    mock_get_text.assert_not_called()

    # Ensure a generic error message was sent to the user
    mock_update_voice.message.reply_text.assert_called_once_with("Произошла ошибка при обработке вашего голосового сообщения.")

    # Ensure file cleanup is not attempted if download fails before file path is fully determined or used
    # Depending on where the exception is, os.path.exists might not be called with the target path.

@pytest.mark.asyncio
async def test_handle_voice_message_no_voice(mock_update_voice, mock_context):
    """Test that the handler does nothing if there's no voice message."""
    # Get the original get_file mock before .voice is set to None
    original_get_file_mock = mock_update_voice.message.voice.get_file

    mock_update_voice.message.voice = None # Simulate no voice message

    await handle_voice_message(mock_update_voice, mock_context)

    original_get_file_mock.assert_not_called()
    mock_update_voice.message.reply_text.assert_not_called()

@pytest.mark.asyncio
@patch('src.bot.handlers.get_text_from_voice', new_callable=AsyncMock)
@patch('src.bot.handlers.os.path.exists')
@patch('src.bot.handlers.os.remove')
async def test_handle_voice_message_cleanup_file_not_exists(mock_os_remove, mock_os_exists, mock_get_text, mock_update_voice, mock_context):
    """Test that os.remove is not called if os.path.exists returns False."""
    mock_get_text.return_value = "Test"
    mock_os_exists.return_value = False # Simulate file does not exist at cleanup

    await handle_voice_message(mock_update_voice, mock_context)

    expected_download_path = "/tmp/test_file_id.ogg"
    mock_os_exists.assert_called_once_with(expected_download_path)
    mock_os_remove.assert_not_called() # Key assertion

@pytest.mark.asyncio
@patch('src.bot.handlers.get_text_from_voice', new_callable=AsyncMock)
@patch('src.bot.handlers.os.path.exists')
@patch('src.bot.handlers.os.remove', side_effect=OSError("Failed to delete"))
async def test_handle_voice_message_cleanup_os_error(mock_os_remove_error, mock_os_exists, mock_get_text, mock_update_voice, mock_context, caplog):
    """Test that an OSError during cleanup is caught and logged."""
    mock_get_text.return_value = "Test"
    mock_os_exists.return_value = True

    await handle_voice_message(mock_update_voice, mock_context)

    expected_download_path = "/tmp/test_file_id.ogg"
    mock_os_exists.assert_called_once_with(expected_download_path)
    mock_os_remove_error.assert_called_once_with(expected_download_path)
    assert f"Error deleting temporary file {expected_download_path}: Failed to delete" in caplog.text
