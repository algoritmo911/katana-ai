import unittest
from unittest.mock import MagicMock, patch, call, AsyncMock
import json
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
        # Create a dummy commands directory for testing
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
        self.mock_datetime.utcnow.return_value.strftime.return_value = "YYYYMMDD_HHMMSS_ffffff"

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

        if self.test_commands_dir.exists():
            shutil.rmtree(self.test_commands_dir, ignore_errors=True)
        if self.test_voice_file_dir.exists():
            shutil.rmtree(self.test_voice_file_dir, ignore_errors=True)

        bot.COMMAND_FILE_DIR = self.original_command_file_dir
        bot.active_gpt_streams.clear()

    def _create_mock_message(self, text_payload):
        mock_message = MagicMock(spec=telebot.types.Message)
        mock_message.chat = MagicMock(spec=telebot.types.Chat)
        mock_message.chat.id = 12345
        mock_message.text = json.dumps(text_payload)
        return mock_message

    def _run_async_test(self, test_func):
        asyncio.run(test_func())

    def test_valid_command_gets_saved(self):
        async def _async_test():
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
            args, kwargs = self.mock_bot_module_instance.reply_to.call_args
            self.assertEqual(args[0], mock_message)
            self.assertTrue(args[1].startswith("✅ Command received and saved as"))
            self.assertIn(str(expected_file_path), args[1])
            found_log = any(f"Successfully validated JSON command from {mock_message.chat.id}: {json.dumps(command)}" in call_arg.args[0] for call_arg in self.mock_log_local_bot_event.call_args_list)
            self.assertTrue(found_log, "Expected log for successful validation with full command data was not found.")
        self._run_async_test(_async_test)

    def test_text_not_nlp_or_json_goes_to_gpt(self):
        async def _async_test():
            mock_message = MagicMock(spec=telebot.types.Message)
            mock_message.chat = MagicMock(spec=telebot.types.Chat)
            mock_message.chat.id = 123
            mock_message.text = "this is plain text, not a command"
            self.mock_openai_chat_completion_create.return_value = iter([])
            with patch('bot.interpret', return_value=None):
                await bot.handle_text_message(mock_message)
            self.mock_openai_chat_completion_create.assert_called_once()
            self.mock_bot_instance.send_chat_action.assert_called_with(123, 'typing')
        self._run_async_test(_async_test)

    def test_missing_type_field(self):
        async def _async_test():
            command = {"module": "test_module", "args": {}, "id": "test_id"}
            mock_message = self._create_mock_message(command)
            with patch('bot.interpret', return_value=None):
                await bot.handle_text_message(mock_message)
            self.mock_bot_instance.reply_to.assert_called_with(mock_message, "Error: Missing required field 'type'.")
        self._run_async_test(_async_test)

    def test_empty_string_type(self):
        async def _async_test():
            command = {"type": "", "module": "test_module", "args": {}, "id": "1"}
            mock_message = self._create_mock_message(command)
            with patch('bot.interpret', return_value=None):
                await bot.handle_text_message(mock_message)
            self.mock_bot_instance.reply_to.assert_called_with(mock_message, "Error: Field 'type' must be a non-empty string. Got value ''.")
        self._run_async_test(_async_test)

    def test_whitespace_string_type(self):
        async def _async_test():
            command = {"type": "   ", "module": "test_module", "args": {}, "id": "1"}
            mock_message = self._create_mock_message(command)
            with patch('bot.interpret', return_value=None):
                await bot.handle_text_message(mock_message)
            self.mock_bot_instance.reply_to.assert_called_with(mock_message, "Error: Field 'type' must be a non-empty string. Got value '   '.")
        self._run_async_test(_async_test)

    def test_missing_module_field(self):
        async def _async_test():
            command = {"type": "test_type", "args": {}, "id": "test_id"}
            mock_message = self._create_mock_message(command)
            with patch('bot.interpret', return_value=None):
                await bot.handle_text_message(mock_message)
            self.mock_bot_instance.reply_to.assert_called_with(mock_message, "Error: Missing required field 'module'.")
        self._run_async_test(_async_test)

    def test_empty_string_module(self):
        async def _async_test():
            command = {"type": "test", "module": "", "args": {}, "id": "1"}
            mock_message = self._create_mock_message(command)
            with patch('bot.interpret', return_value=None):
                await bot.handle_text_message(mock_message)
            self.mock_bot_instance.reply_to.assert_called_with(mock_message, "Error: Field 'module' must be a non-empty string. Got value ''.")
        self._run_async_test(_async_test)

    def test_whitespace_string_module(self):
        async def _async_test():
            command = {"type": "test", "module": "   ", "args": {}, "id": "1"}
            mock_message = self._create_mock_message(command)
            with patch('bot.interpret', return_value=None):
                await bot.handle_text_message(mock_message)
            self.mock_bot_instance.reply_to.assert_called_with(mock_message, "Error: Field 'module' must be a non-empty string. Got value '   '.")
        self._run_async_test(_async_test)

    def test_invalid_args_type(self):
        async def _async_test():
            command = {"type": "test_type", "module": "test_module", "args": "not_a_dict", "id": "test_id"}
            mock_message = self._create_mock_message(command)
            with patch('bot.interpret', return_value=None):
                await bot.handle_text_message(mock_message)
            self.mock_bot_instance.reply_to.assert_called_with(mock_message, "Error: Field 'args' must be type dict. Got value 'not_a_dict' of type str.")
        self._run_async_test(_async_test)

    def test_invalid_id_type(self):
        async def _async_test():
            command = {"type": "test_type", "module": "test_module", "args": {}, "id": [1,2,3]}
            mock_message = self._create_mock_message(command)
            with patch('bot.interpret', return_value=None):
                await bot.handle_text_message(mock_message)
            self.mock_bot_instance.reply_to.assert_called_with(mock_message, "Error: Field 'id' must be type str or int. Got value '[1, 2, 3]' of type list.")
        self._run_async_test(_async_test)

    def test_valid_command_with_int_id(self):
        async def _async_test():
            command = {"type": "test_type_int_id", "module": "test_module_int_id", "args": {}, "id": 123}
            mock_message = self._create_mock_message(command)
            with patch('bot.interpret', return_value=None):
                await bot.handle_text_message(mock_message)
            expected_module_dir = self.test_commands_dir / "telegram_mod_test_module_int_id"
            self.assertTrue(expected_module_dir.exists())
            expected_filename = f"YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
            expected_file_path = expected_module_dir / expected_filename
            self.assertTrue(expected_file_path.exists())
            with open(expected_file_path, "r") as f:
                saved_data = json.load(f)
            self.assertEqual(saved_data, command)
            self.mock_bot_instance.reply_to.assert_called_once()
            args, kwargs = self.mock_bot_instance.reply_to.call_args
            self.assertTrue(args[1].startswith("✅ Command received and saved as"))
            found_log = any(f"Successfully validated JSON command from {mock_message.chat.id}: {json.dumps(command)}" in call_arg.args[0] for call_arg in self.mock_log_local_bot_event.call_args_list)
            self.assertTrue(found_log, "Expected log for successful validation with full command data (int id) was not found.")
        self._run_async_test(_async_test)

    def test_valid_command_with_empty_args(self):
        async def _async_test():
            command = {"type": "test_empty_args", "module": "test_mod_empty_args", "args": {}, "id": "empty_args_id"}
            mock_message = self._create_mock_message(command)
            with patch('bot.interpret', return_value=None):
                await bot.handle_text_message(mock_message)
            expected_module_dir = self.test_commands_dir / "telegram_mod_test_mod_empty_args"
            self.assertTrue(expected_module_dir.exists())
            expected_filename = f"YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
            expected_file_path = expected_module_dir / expected_filename
            self.assertTrue(expected_file_path.exists())
            self.mock_bot_instance.reply_to.assert_called_once()
        self._run_async_test(_async_test)

    def test_valid_command_with_simple_args(self):
        async def _async_test():
            command = {"type": "test_simple_args", "module": "test_mod_simple_args", "args": {"key": "value"}, "id": "simple_args_id"}
            mock_message = self._create_mock_message(command)
            with patch('bot.interpret', return_value=None):
                await bot.handle_text_message(mock_message)
            expected_module_dir = self.test_commands_dir / "telegram_mod_test_mod_simple_args"
            self.assertTrue(expected_module_dir.exists())
            expected_filename = f"YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
            expected_file_path = expected_module_dir / expected_filename
            self.assertTrue(expected_file_path.exists())
            self.mock_bot_instance.reply_to.assert_called_once()
        self._run_async_test(_async_test)

    @patch('bot.handle_log_event', new_callable=AsyncMock)
    def test_routing_log_event(self, mock_handle_log_event_func):
        async def _async_test():
            command = {"type": "log_event", "module": "logging", "args": {"message": "hello"}, "id": "log001"}
            mock_message = self._create_mock_message(command)
            with patch('bot.interpret', return_value=None):
                await bot.handle_text_message(mock_message)
            mock_handle_log_event_func.assert_called_once_with(command, mock_message.chat.id)
            self.mock_bot_instance.reply_to.assert_called_with(mock_message, "✅ 'log_event' processed (placeholder).")
        self._run_async_test(_async_test)

    @patch('bot.handle_mind_clearing', new_callable=AsyncMock)
    def test_routing_mind_clearing(self, mock_handle_mind_clearing_func):
        async def _async_test():
            command = {"type": "mind_clearing", "module": "wellness", "args": {"duration": "10m"}, "id": "mind002"}
            mock_message = self._create_mock_message(command)
            with patch('bot.interpret', return_value=None):
                await bot.handle_text_message(mock_message)
            mock_handle_mind_clearing_func.assert_called_once_with(command, mock_message.chat.id)
            self.mock_bot_instance.reply_to.assert_called_with(mock_message, "✅ 'mind_clearing' processed (placeholder).")
        self._run_async_test(_async_test)

    def test_unknown_command_type_saves_normally(self):
        async def _async_test():
            command = {"type": "unknown_type", "module": "custom_module", "args": {}, "id": "custom003"}
            mock_message = self._create_mock_message(command)
            with patch('bot.interpret', return_value=None):
                await bot.handle_text_message(mock_message)
            expected_module_dir = self.test_commands_dir / "telegram_mod_custom_module"
            self.assertTrue(expected_module_dir.exists())
            expected_filename = f"YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
            expected_file_path = expected_module_dir / expected_filename
            self.assertTrue(expected_file_path.exists())
            with open(expected_file_path, "r") as f:
                saved_data = json.load(f)
            self.assertEqual(saved_data, command)
            self.mock_bot_instance.reply_to.assert_called_once()
            args, kwargs = self.mock_bot_instance.reply_to.call_args
            self.assertEqual(args[0], mock_message)
            self.assertTrue(args[1].startswith("✅ Command received and saved as"))
            self.assertIn(str(expected_file_path), args[1])
        self._run_async_test(_async_test)

    def test_validation_failure_logs_details(self):
        async def _async_test():
            command = {"type": "test_type", "module": "", "args": {}, "id": "fail_log_id"}
            original_command_text = json.dumps(command)
            mock_message = self._create_mock_message(command)
            with patch('bot.interpret', return_value=None):
                await bot.handle_text_message(mock_message)
            self.mock_bot_instance.reply_to.assert_called_with(mock_message, "Error: Field 'module' must be a non-empty string. Got value ''.")
            expected_log_part = "Validation failed for 12345: Error: Field 'module' must be a non-empty string. Got value ''."
            expected_command_part = f"(Command: {original_command_text})"
            found_log = any(expected_log_part in call.args[0] and expected_command_part in call.args[0] for call in self.mock_log_local_bot_event.call_args_list)
            self.assertTrue(found_log, f"Expected log with validation failure details was not found.")
        self._run_async_test(_async_test)

    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data=b"dummy voice data")
    def test_get_text_from_voice_success(self, mock_open_file):
        async def _async_test():
            self.mock_openai_transcribe.return_value = {'text': 'Hello world'}
            result = await bot.get_text_from_voice("dummy_path.ogg")
            self.assertEqual(result, "Hello world")
            mock_open_file.assert_called_once_with("dummy_path.ogg", "rb")
            self.mock_openai_transcribe.assert_called_once()
            self.mock_log_local_bot_event.assert_any_call("Sending voice file dummy_path.ogg to OpenAI Whisper API...")
            self.mock_log_local_bot_event.assert_any_call("Voice transcribed successfully: 'Hello world'")
        self._run_async_test(_async_test)

    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data=b"dummy voice data")
    def test_get_text_from_voice_api_error(self, mock_open_file):
        async def _async_test():
            self.mock_openai_transcribe.side_effect = bot.openai.APIError("API Error", request=MagicMock(), body=None)
            result = await bot.get_text_from_voice("dummy_path.ogg")
            self.assertIsNone(result)
            self.mock_log_local_bot_event.assert_any_call("OpenAI API Error during voice transcription: API Error")
        self._run_async_test(_async_test)

    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data=b"dummy voice data")
    def test_get_text_from_voice_no_text_returned(self, mock_open_file):
        async def _async_test():
            self.mock_openai_transcribe.return_value = {'text': None}
            result = await bot.get_text_from_voice("dummy_path.ogg")
            self.assertIsNone(result)
            self.mock_log_local_bot_event.assert_any_call("Voice transcription returned no text (text is None).")
        self._run_async_test(_async_test)

    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data=b"dummy voice data")
    def test_get_text_from_voice_api_returns_empty_string(self, mock_open_file):
        async def _async_test():
            self.mock_openai_transcribe.return_value = {'text': ""}
            result = await bot.get_text_from_voice("dummy_path.ogg")
            self.assertEqual(result, "")
            self.mock_log_local_bot_event.assert_any_call("Voice transcribed successfully: ''")
        self._run_async_test(_async_test)

    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data=b"dummy voice data")
    def test_get_text_from_voice_api_returns_whitespace_string(self, mock_open_file):
        async def _async_test():
            self.mock_openai_transcribe.return_value = {'text': "  "}
            result = await bot.get_text_from_voice("dummy_path.ogg")
            self.assertEqual(result, "")
            self.mock_log_local_bot_event.assert_any_call("Voice transcribed successfully: '  '")
        self._run_async_test(_async_test)

    @patch('bot.OPENAI_API_KEY', None)
    def test_get_text_from_voice_no_api_key(self):
        async def _async_test():
            result = await bot.get_text_from_voice("dummy_path.ogg")
            self.assertIsNone(result)
            self.mock_log_local_bot_event.assert_any_call("OpenAI API key not configured. Cannot process voice.")
            self.mock_openai_transcribe.assert_not_called()
        self._run_async_test(_async_test)

    @patch('builtins.open', side_effect=IOError("File not found"))
    def test_get_text_from_voice_file_open_error(self, mock_open_file):
        async def _async_test():
            with patch('bot.OPENAI_API_KEY', 'fake_key_for_this_test'):
                result = await bot.get_text_from_voice("dummy_path.ogg")
                self.assertIsNone(result)
                self.mock_log_local_bot_event.assert_any_call("Unexpected error during voice transcription: File not found")
        self._run_async_test(_async_test)

    def _create_mock_voice_message(self):
        mock_message = MagicMock(spec=telebot.types.Message)
        mock_message.chat = MagicMock(spec=telebot.types.Chat)
        mock_message.chat.id = 67890
        mock_message.voice = MagicMock(spec=telebot.types.Voice)
        mock_message.voice.file_id = "test_voice_file_id"
        mock_message.voice.duration = 3
        mock_message.message_id = 123
        mock_message.date = 1678886400
        mock_message.from_user = MagicMock(spec=telebot.types.User)
        mock_message.from_user.id = 98765
        return mock_message

    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_handle_voice_message_success(self, mock_open_file):
        async def _async_test():
            self.mock_get_text_from_voice = self.get_text_from_voice_patcher.start()
            mock_message = self._create_mock_voice_message()
            self.mock_bot_instance.get_file.return_value = MagicMock(file_path="voice/file.oga")
            self.mock_bot_instance.download_file.return_value = b"dummy voice data"
            self.mock_get_text_from_voice.return_value = "show disk space"
            self.mock_openai_chat_completion_create.return_value = iter([])
            await bot.handle_voice_message(mock_message)
            self.mock_bot_instance.get_file.assert_called_once_with("test_voice_file_id")
            self.mock_bot_instance.download_file.assert_called_once_with("voice/file.oga")
            expected_temp_path = self.test_voice_file_dir / f"{mock_message.voice.file_id}.ogg"
            mock_open_file.assert_called_once_with(expected_temp_path, 'wb')
            mock_open_file().write.assert_called_once_with(b"dummy voice data")
            self.mock_get_text_from_voice.assert_called_once_with(str(expected_temp_path))
            self.mock_bot_instance.reply_to.assert_any_call(mock_message, '🗣️ Распознано: "show disk space"')
            self.mock_openai_chat_completion_create.assert_called_once()
            args_list = self.mock_openai_chat_completion_create.call_args_list
            self.assertEqual(args_list[0].kwargs['messages'][-1]['content'], "show disk space")
            self.mock_path_exists.return_value = True
            await asyncio.sleep(0.01)
            self.mock_os_remove.assert_called_once_with(expected_temp_path)
            self.get_text_from_voice_patcher.stop()
        self._run_async_test(_async_test)

    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_handle_voice_message_transcription_fails(self, mock_open_file):
        async def _async_test():
            self.mock_get_text_from_voice = self.get_text_from_voice_patcher.start()
            mock_message = self._create_mock_voice_message()
            self.mock_bot_instance.get_file.return_value = MagicMock(file_path="voice/file.oga")
            self.mock_bot_instance.download_file.return_value = b"dummy voice data"
            self.mock_get_text_from_voice.return_value = None
            await bot.handle_voice_message(mock_message)
            expected_temp_path = self.test_voice_file_dir / f"{mock_message.voice.file_id}.ogg"
            self.mock_get_text_from_voice.assert_called_once_with(str(expected_temp_path))
            self.mock_bot_instance.reply_to.assert_any_call(mock_message, "Не понял, повтори, пожалуйста. 🎙️")
            self.mock_openai_chat_completion_create.assert_not_called()
            await asyncio.sleep(0.01)
            self.mock_os_remove.assert_called_once_with(expected_temp_path)
            self.get_text_from_voice_patcher.stop()
        self._run_async_test(_async_test)

    @patch('bot.OPENAI_API_KEY', None)
    def test_handle_voice_message_no_openai_key(self):
        async def _async_test():
            mock_message = self._create_mock_voice_message()
            await bot.handle_voice_message(mock_message)
            self.mock_bot_instance.reply_to.assert_called_with(mock_message, "⚠️ Распознавание голоса не настроено на сервере.")
            self.mock_bot_instance.get_file.assert_not_called()
            if hasattr(self.mock_get_text_from_voice, 'assert_not_called'):
                self.mock_get_text_from_voice.assert_not_called()
            self.mock_openai_chat_completion_create.assert_not_called()
        self._run_async_test(_async_test)

    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_handle_voice_message_download_exception(self, mock_open_file):
        async def _async_test():
            mock_message = self._create_mock_voice_message()
            self.mock_bot_instance.get_file.side_effect = Exception("Download error")
            await bot.handle_voice_message(mock_message)
            self.mock_bot_instance.reply_to.assert_called_with(mock_message, "Произошла ошибка при обработке голосового сообщения. 😥")
            if hasattr(self.mock_get_text_from_voice, 'assert_not_called'):
                self.mock_get_text_from_voice.assert_not_called()
            self.mock_os_remove.assert_not_called()
        self._run_async_test(_async_test)

    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    @patch('os.remove', side_effect=OSError("Delete failed"))
    def test_handle_voice_message_cleanup_exception(self, mock_os_remove_custom, mock_open_file):
        async def _async_test():
            self.mock_get_text_from_voice = self.get_text_from_voice_patcher.start()
            mock_message = self._create_mock_voice_message()
            self.mock_bot_instance.get_file.return_value = MagicMock(file_path="voice/file.oga")
            self.mock_bot_instance.download_file.return_value = b"dummy voice data"
            self.mock_get_text_from_voice.return_value = "текст"
            self.mock_openai_chat_completion_create.return_value = iter([])
            await bot.handle_voice_message(mock_message)
            expected_temp_path = self.test_voice_file_dir / f"{mock_message.voice.file_id}.ogg"
            self.mock_openai_chat_completion_create.assert_called_once()
            self.mock_bot_instance.reply_to.assert_any_call(mock_message, '🗣️ Распознано: "текст"')
            await asyncio.sleep(0.01)
            mock_os_remove_custom.assert_called_once_with(expected_temp_path)
            self.mock_log_local_bot_event.assert_any_call(f"Error deleting temporary voice file {expected_temp_path}: Delete failed")
            self.get_text_from_voice_patcher.stop()
        self._run_async_test(_async_test)

    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    @patch('bot.process_user_message', new_callable=AsyncMock)
    def test_handle_voice_message_transcription_returns_empty_string(self, mock_process_user_message, mock_open_file):
        async def _async_test():
            self.mock_get_text_from_voice = self.get_text_from_voice_patcher.start()
            mock_original_voice_message = self._create_mock_voice_message()
            self.mock_bot_instance.get_file.return_value = MagicMock(file_path="voice/file.oga")
            self.mock_bot_instance.download_file.return_value = b"dummy voice data"
            self.mock_get_text_from_voice.return_value = ""
            await bot.handle_voice_message(mock_original_voice_message)
            expected_temp_path = self.test_voice_file_dir / f"{mock_original_voice_message.voice.file_id}.ogg"
            self.mock_get_text_from_voice.assert_called_once_with(str(expected_temp_path))
            self.mock_bot_instance.reply_to.assert_any_call(mock_original_voice_message, '🗣️ Распознано: ""')
            mock_process_user_message.assert_called_once_with(mock_original_voice_message.chat.id, "", mock_original_voice_message)
            await asyncio.sleep(0.01)
            self.mock_os_remove.assert_called_once_with(expected_temp_path)
            self.get_text_from_voice_patcher.stop()
        self._run_async_test(_async_test)

    def test_handle_voice_message_get_file_exception(self):
        async def _async_test():
            mock_message = self._create_mock_voice_message()
            self.mock_bot_instance.get_file.side_effect = Exception("TG API get_file error")
            await bot.handle_voice_message(mock_message)
            self.mock_bot_instance.reply_to.assert_called_with(mock_message, "Произошла ошибка при обработке голосового сообщения. 😥")
            if hasattr(self.mock_get_text_from_voice, 'assert_not_called'):
                self.mock_get_text_from_voice.assert_not_called()
            self.mock_os_remove.assert_not_called()
        self._run_async_test(_async_test)

    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_handle_voice_message_download_file_exception(self, mock_open_file):
        async def _async_test():
            mock_message = self._create_mock_voice_message()
            self.mock_bot_instance.get_file.return_value = MagicMock(file_path="voice/file.oga")
            self.mock_bot_instance.download_file.side_effect = Exception("TG API download_file error")
            await bot.handle_voice_message(mock_message)
            self.mock_bot_instance.reply_to.assert_called_with(mock_message, "Произошла ошибка при обработке голосового сообщения. 😥")
            if hasattr(self.mock_get_text_from_voice, 'assert_not_called'):
                self.mock_get_text_from_voice.assert_not_called()
            self.mock_os_remove.assert_not_called()
        self._run_async_test(_async_test)

    @patch('builtins.open', side_effect=IOError("Disk full error"))
    def test_handle_voice_message_save_temp_file_ioerror(self, mock_open_file_error):
        async def _async_test():
            mock_message = self._create_mock_voice_message()
            self.mock_bot_instance.get_file.return_value = MagicMock(file_path="voice/file.oga")
            self.mock_bot_instance.download_file.return_value = b"dummy voice data"
            await bot.handle_voice_message(mock_message)
            self.mock_bot_instance.reply_to.assert_called_with(mock_message, "Произошла ошибка при обработке голосового сообщения. 😥")
            if hasattr(self.mock_get_text_from_voice, 'assert_not_called'):
                self.mock_get_text_from_voice.assert_not_called()
            await asyncio.sleep(0.01)
            self.mock_os_remove.assert_not_called()
        self._run_async_test(_async_test)

    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data=b"dummy voice data")
    def test_get_text_from_voice_simulating_rate_limit_error(self, mock_open_file):
        async def _async_test():
            mock_response = MagicMock()
            mock_response.status_code = 429
            try:
                from openai import RateLimitError as OpenAIRateLimitError
                rate_limit_error_instance = OpenAIRateLimitError("Rate limit exceeded", response=mock_response, body=None)
            except ImportError:
                rate_limit_error_instance = bot.openai.APIError("Simulated Rate Limit Error", request=MagicMock(), body=None)
            self.mock_openai_transcribe.side_effect = rate_limit_error_instance
            result = await bot.get_text_from_voice("dummy_path.ogg")
            self.assertIsNone(result)
            if isinstance(rate_limit_error_instance, bot.openai.RateLimitError):
                self.mock_log_local_bot_event.assert_any_call("OpenAI API Error during voice transcription: Rate limit exceeded")
            else:
                self.mock_log_local_bot_event.assert_any_call("OpenAI API Error during voice transcription: Simulated Rate Limit Error")
        self._run_async_test(_async_test)

    @patch('builtins.open', new_callable=MagicMock)
    def test_get_text_from_voice_short_and_long_audio_simulation(self, mock_open):
        async def _async_test():
            mock_file_short = MagicMock(); mock_file_short.read.return_value = b"short audio data"; mock_file_short.__enter__.return_value = mock_file_short; mock_file_short.__exit__.return_value = None
            mock_file_long = MagicMock(); mock_file_long.read.return_value = b"very long audio data"; mock_file_long.__enter__.return_value = mock_file_long; mock_file_long.__exit__.return_value = None
            mock_open.side_effect = [mock_file_short, mock_file_long]
            self.mock_openai_transcribe.return_value = {'text': 'Hi'}
            result_short = await bot.get_text_from_voice("short_audio.ogg")
            self.assertEqual(result_short, "Hi")
            mock_open.assert_any_call("short_audio.ogg", "rb")
            self.assertTrue(self.mock_openai_transcribe.called)
            self.mock_openai_transcribe.reset_mock()
            self.mock_openai_transcribe.return_value = {'text': 'This is a longer transcription.'}
            result_long = await bot.get_text_from_voice("long_audio.ogg")
            self.assertEqual(result_long, "This is a longer transcription.")
            mock_open.assert_any_call("long_audio.ogg", "rb")
            self.assertTrue(self.mock_openai_transcribe.called)
            self.assertEqual(mock_open.call_count, 2)
            self.assertEqual(self.mock_openai_transcribe.call_count, 1)
        self._run_async_test(_async_test)

    def test_gpt_streaming_sends_chunks(self):
        async def _async_test():
            mock_stream_chunks = [{"choices": [{"delta": {"content": "Hello"}}]}, {"choices": [{"delta": {"content": ", "}}]}, {"choices": [{"delta": {"content": "world!"}}]}, {"choices": [{"delta": {}}]}]
            self.mock_openai_chat_completion_create.return_value = iter(mock_stream_chunks)
            mock_message = self._create_mock_message("some non-command text")
            mock_message.text = "tell me a joke"
            mock_message.chat.id = 12345
            with patch('bot.interpret', return_value=None):
                await bot.handle_text_message(mock_message)
            self.mock_bot_instance.send_chat_action.assert_called_once_with(12345, 'typing')
            self.mock_bot_instance.reply_to.assert_any_call(mock_message, "Hello")
            mock_sent_message = MagicMock(); mock_sent_message.message_id = 98765
            self.mock_bot_instance.reply_to.return_value = mock_sent_message
            self.mock_bot_instance.reply_to.reset_mock()
            self.mock_bot_instance.edit_message_text.reset_mock()
            self.mock_openai_chat_completion_create.return_value = iter(mock_stream_chunks)
            with patch('bot.interpret', return_value=None):
                await bot.handle_text_message(mock_message)
            self.mock_bot_instance.reply_to.assert_called_once_with(mock_message, "Hello")
            calls = [call("Hello, ", 12345, 98765), call("Hello, world!", 12345, 98765)]
            self.mock_bot_instance.edit_message_text.assert_has_calls(calls, any_order=False)
            self.assertEqual(self.mock_bot_instance.edit_message_text.call_count, 2)
            self.mock_openai_chat_completion_create.assert_called_once_with(model="gpt-3.5-turbo", messages=[{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": "tell me a joke"}], stream=True)
        self._run_async_test(_async_test)

    def test_gpt_stream_cancellation_by_new_message(self):
        async def _async_test():
            chat_id = 111222
            first_message_text = "Tell me a very long story"
            second_message_text = "Actually, stop and tell me a joke"
            first_stream_chunks = ["Part1", "Part2", "Part3", "Part4", "Part5"]
            seen_cancel_events = []
            async def first_stream_gen_wrapper(*args, **kwargs):
                active_task_info = bot.active_gpt_streams.get(chat_id)
                current_cancel_event = active_task_info[1] if active_task_info else None
                if current_cancel_event: seen_cancel_events.append(current_cancel_event)
                return mock_openai_stream_generator(first_stream_chunks, delay=0.1, cancel_event_check=current_cancel_event)
            async def second_stream_gen_wrapper(*args, **kwargs):
                active_task_info = bot.active_gpt_streams.get(chat_id)
                current_cancel_event = active_task_info[1] if active_task_info else None
                if current_cancel_event: seen_cancel_events.append(current_cancel_event)
                return mock_openai_stream_generator(["Joke!", " Ha ha!"], delay=0.01, cancel_event_check=current_cancel_event)
            self.mock_openai_chat_completion_create.side_effect = [first_stream_gen_wrapper(), second_stream_gen_wrapper()]
            mock_msg1 = MagicMock(spec=telebot.types.Message); mock_msg1.chat = MagicMock(spec=telebot.types.Chat); mock_msg1.chat.id = chat_id; mock_msg1.text = first_message_text; mock_msg1.message_id = 1000
            mock_msg2 = MagicMock(spec=telebot.types.Message); mock_msg2.chat = MagicMock(spec=telebot.types.Chat); mock_msg2.chat.id = chat_id; mock_msg2.text = second_message_text; mock_msg2.message_id = 1001
            mock_bot_sent_msg1 = MagicMock(spec=telebot.types.Message); mock_bot_sent_msg1.message_id = 2000
            mock_bot_sent_msg2 = MagicMock(spec=telebot.types.Message); mock_bot_sent_msg2.message_id = 2001
            self.mock_bot_instance.reply_to.side_effect = [mock_bot_sent_msg1, mock_bot_sent_msg2]
            with patch('bot.interpret', return_value=None):
                asyncio.create_task(bot.process_user_message(chat_id, mock_msg1.text, mock_msg1))
            await asyncio.sleep(0.05)
            self.mock_bot_instance.send_chat_action.assert_any_call(chat_id, 'typing')
            self.mock_bot_instance.reply_to.assert_any_call(mock_msg1, "Part1")
            self.assertEqual(len(bot.active_gpt_streams), 1, "One active stream should exist")
            self.assertIn(chat_id, bot.active_gpt_streams, "Chat ID should be in active streams")
            original_task, original_cancel_event, _ = bot.active_gpt_streams[chat_id]
            await asyncio.sleep(0.15)
            self.mock_bot_instance.edit_message_text.assert_any_call("Part1Part2", chat_id, mock_bot_sent_msg1.message_id)
            with patch('bot.interpret', return_value=None):
                asyncio.create_task(bot.process_user_message(chat_id, mock_msg2.text, mock_msg2))
            await asyncio.sleep(0.05)
            self.assertTrue(original_cancel_event.is_set(), "Original stream's cancellation event was not set.")
            await asyncio.sleep(0.3)
            first_message_edits = [call_obj.args[0] for call_obj in self.mock_bot_instance.edit_message_text.call_args_list if call_obj.args[2] == mock_bot_sent_msg1.message_id]
            self.assertNotIn("Part1Part2Part3", first_message_edits, "Stream 1 should have been cancelled before Part3")
            self.assertLessEqual(len(first_message_edits), 2, "Stream 1 should not have too many edits after interruption")
            self.mock_bot_instance.reply_to.assert_any_call(mock_msg2, "Joke!")
            await asyncio.sleep(0.5)
            if chat_id in bot.active_gpt_streams:
                current_task, _, current_msg_id = bot.active_gpt_streams[chat_id]
                self.assertNotEqual(current_task, original_task, "The active task should be the new one if any.")
                self.assertEqual(current_msg_id, mock_bot_sent_msg2.message_id, "Active stream should be for the second message if any.")
            self.assertEqual(self.mock_openai_chat_completion_create.call_count, 2)
        self._run_async_test(_async_test)


if __name__ == '__main__':
    unittest.main()
