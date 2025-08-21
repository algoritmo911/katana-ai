import unittest
from unittest.mock import MagicMock, patch, call, AsyncMock
import json
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from pathlib import Path
import shutil # For robust directory removal

# Assuming bot.py is in the same directory or accessible in PYTHONPATH
import bot
import telebot # Added import
import asyncio # For asyncio.sleep and Event in tests

# Helper async generator for mocking OpenAI stream with controllable delay/cancellation
async def mock_openai_stream_generator(chunks_data, delay=0.01, cancel_event_check=None):
    """
    Simulates the OpenAI streaming API.
    - chunks_data: A list of strings, each being a content of a chunk.
    - delay: Time to sleep after yielding each chunk.
    - cancel_event_check: An asyncio.Event to check for cancellation.
    """
    try:
        for chunk_content in chunks_data:
            if cancel_event_check and cancel_event_check.is_set():
                break
            yield {"choices": [{"delta": {"content": chunk_content}}]}
            if delay > 0:
                await asyncio.sleep(delay)
    except asyncio.CancelledError:
        raise
    finally:
        pass
    if not (cancel_event_check and cancel_event_check.is_set()):
        yield {"choices": [{"delta": {}}]}


class TestBot(unittest.TestCase):

    def setUp(self):
        self.test_commands_dir = Path("test_commands_temp_dir")
        self.test_commands_dir.mkdir(parents=True, exist_ok=True)
        self.original_command_file_dir = bot.COMMAND_FILE_DIR
        bot.COMMAND_FILE_DIR = self.test_commands_dir
        self.mock_bot_instance = MagicMock(spec=telebot.async_telebot.AsyncTeleBot)
        self.mock_bot_instance.send_message = AsyncMock()
        self.mock_bot_instance.reply_to = AsyncMock()
        self.mock_bot_instance.edit_message_text = AsyncMock()
        self.mock_bot_instance.send_chat_action = AsyncMock()
        self.mock_bot_instance.get_file = AsyncMock()
        self.mock_bot_instance.download_file = AsyncMock()
        self.bot_patcher = patch('bot.bot', self.mock_bot_instance)
        self.mock_bot_module_instance = self.bot_patcher.start()
        self.mock_datetime_patcher = patch('bot.datetime')
        self.mock_datetime = self.mock_datetime_patcher.start()
        self.mock_datetime.now.return_value.strftime.return_value = "YYYYMMDD_HHMMSS_ffffff"
        self.mock_log_event_patcher = patch('bot.log_local_bot_event')
        self.mock_log_local_bot_event = self.mock_log_event_patcher.start()
        self.openai_api_key_patcher = patch('bot.OPENAI_API_KEY', 'test_openai_key')
        self.mock_openai_api_key = self.openai_api_key_patcher.start()
        self.openai_transcribe_patcher = patch('openai.Audio.transcribe')
        self.mock_openai_transcribe = self.openai_transcribe_patcher.start()
        self.get_text_from_voice_patcher = patch('bot.get_text_from_voice', new_callable=AsyncMock)
        self.mock_get_text_from_voice = None
        self.openai_chat_completion_patcher = patch('openai.ChatCompletion.create')
        self.mock_openai_chat_completion_create = self.openai_chat_completion_patcher.start()
        self.os_remove_patcher = patch('os.remove')
        self.mock_os_remove = self.os_remove_patcher.start()
        self.path_exists_patcher = patch('pathlib.Path.exists')
        self.mock_path_exists = self.path_exists_patcher.start()
        self.mock_path_exists.return_value = True
        self.test_voice_file_dir = Path("test_voice_temp_dir")
        self.test_voice_file_dir.mkdir(parents=True, exist_ok=True)
        self.voice_file_dir_patcher = patch('bot.VOICE_FILE_DIR', self.test_voice_file_dir)
        self.voice_file_dir_patcher.start()
        # Also mock the agent instance to check calls to it
        self.katana_agent_patcher = patch('bot.katana_agent_instance', autospec=True)
        self.mock_katana_agent = self.katana_agent_patcher.start()


    def tearDown(self):
        self.bot_patcher.stop()
        self.mock_datetime_patcher.stop()
        self.mock_log_event_patcher.stop()
        self.openai_api_key_patcher.stop()
        self.openai_transcribe_patcher.stop()
        self.openai_chat_completion_patcher.stop()
        if self.mock_get_text_from_voice is not None:
            try:
                self.get_text_from_voice_patcher.stop()
            except RuntimeError:
                pass
        self.os_remove_patcher.stop()
        self.path_exists_patcher.stop()
        self.voice_file_dir_patcher.stop()
        self.katana_agent_patcher.stop()

        if self.test_commands_dir.exists():
            shutil.rmtree(self.test_commands_dir)
        if self.test_voice_file_dir.exists():
            shutil.rmtree(self.test_voice_file_dir)

        bot.COMMAND_FILE_DIR = self.original_command_file_dir
        bot.active_gpt_streams.clear()


    def _create_mock_message(self, text_payload):
        mock_message = MagicMock(spec=telebot.types.Message)
        mock_message.chat = MagicMock(spec=telebot.types.Chat)
        mock_message.chat.id = 12345
        mock_message.text = json.dumps(text_payload)
        return mock_message

    def _run_async(self, coro):
        return asyncio.run(coro)

    def test_valid_command_gets_saved(self):
        async def test_body():
            command = {"type": "test_type", "module": "test_module", "args": {}, "id": "test_id"}
            mock_message = self._create_mock_message(command)
            with patch('bot.interpret', return_value=None):
                await bot.handle_text_message(mock_message)
            expected_module_dir = self.test_commands_dir / "telegram_mod_test_module"
            self.assertTrue(expected_module_dir.exists())
            expected_filename = f"YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
            expected_file_path = expected_module_dir / expected_filename
            self.assertTrue(expected_file_path.exists())
            with open(expected_file_path, "r") as f:
                saved_data = json.load(f)
            self.assertEqual(saved_data, command)
            self.mock_bot_module_instance.reply_to.assert_called_once()
            args, _ = self.mock_bot_module_instance.reply_to.call_args
            self.assertEqual(args[0], mock_message)
            self.assertTrue(args[1].startswith("✅ Command received and saved as"))
        self._run_async(test_body())

    def test_text_not_nlp_or_json_goes_to_agent(self):
        async def test_body():
            mock_message = MagicMock(spec=telebot.types.Message)
            mock_message.chat = MagicMock(spec=telebot.types.Chat)
            mock_message.chat.id = 123
            mock_message.text = "this is plain text, not a command"
            self.mock_katana_agent.get_response.return_value = "Agent response"
            with patch('bot.interpret', return_value=None):
                await bot.handle_text_message(mock_message)
            self.mock_katana_agent.get_response.assert_called_once()
            self.mock_bot_instance.reply_to.assert_called_once_with(mock_message, "Agent response")
        self._run_async(test_body())

    def test_missing_type_field(self):
        async def test_body():
            command = {"module": "test_module", "args": {}, "id": "test_id"}
            mock_message = self._create_mock_message(command)
            with patch('bot.interpret', return_value=None):
                await bot.handle_text_message(mock_message)
            self.mock_bot_instance.reply_to.assert_called_with(mock_message, "Error: Missing required field 'type'.")
        self._run_async(test_body())

    @patch('bot.handle_log_event', new_callable=AsyncMock)
    def test_routing_log_event(self, mock_handle_log_event_func):
        async def test_body():
            command = {"type": "log_event", "module": "logging", "args": {"message": "hello"}, "id": "log001"}
            mock_message = self._create_mock_message(command)
            with patch('bot.interpret', return_value=None):
                await bot.handle_text_message(mock_message)
            mock_handle_log_event_func.assert_called_once_with(command, mock_message.chat.id)
            self.mock_bot_instance.reply_to.assert_called_with(mock_message, "✅ 'log_event' processed.")
        self._run_async(test_body())

    def _create_mock_voice_message(self):
        mock_message = MagicMock(spec=telebot.types.Message)
        mock_message.chat = MagicMock(spec=telebot.types.Chat)
        mock_message.chat.id = 67890
        mock_message.voice = MagicMock(spec=telebot.types.Voice)
        mock_message.voice.file_id = "test_voice_file_id"
        return mock_message

    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_handle_voice_message_success(self, mock_open_file):
        async def test_body():
            self.mock_get_text_from_voice = self.get_text_from_voice_patcher.start()
            mock_message = self._create_mock_voice_message()
            self.mock_bot_instance.get_file.return_value = MagicMock(file_path="voice/file.oga")
            self.mock_bot_instance.download_file.return_value = b"dummy voice data"
            self.mock_get_text_from_voice.return_value = "show disk space"
            self.mock_katana_agent.get_response.return_value = "Agent response"
            with patch('bot.interpret', return_value=None):
                await bot.handle_voice_message(mock_message)
            self.mock_bot_instance.get_file.assert_called_once_with("test_voice_file_id")
            self.mock_bot_instance.download_file.assert_called_once_with("voice/file.oga")
            expected_temp_path = self.test_voice_file_dir / f"{mock_message.voice.file_id}.ogg"
            mock_open_file.assert_called_once_with(expected_temp_path, 'wb')
            self.mock_get_text_from_voice.assert_called_once_with(str(expected_temp_path))
            self.mock_bot_instance.reply_to.assert_any_call(mock_message, '🗣️ Распознано: "show disk space"')
            self.mock_katana_agent.get_response.assert_called_once()
            self.mock_os_remove.assert_called_once_with(expected_temp_path)
            self.get_text_from_voice_patcher.stop()
        self._run_async(test_body())


if __name__ == '__main__':
    unittest.main()
