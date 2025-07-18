import unittest
from unittest.mock import MagicMock, patch, call, AsyncMock
import json
from pathlib import Path
import shutil  # For robust directory removal

# Assuming bot.py is in the same directory or accessible in PYTHONPATH
import bot
import telebot  # Added import
import asyncio  # For asyncio.sleep and Event in tests


class TestBot(unittest.TestCase):

    def setUp(self):
        # Create a dummy commands directory for testing
        self.test_commands_dir = Path(
            "test_commands_temp_dir"
        )  # Using a more unique name
        self.test_commands_dir.mkdir(parents=True, exist_ok=True)

        # Store original and set to test
        self.original_command_file_dir = bot.COMMAND_FILE_DIR
        bot.COMMAND_FILE_DIR = self.test_commands_dir

        # Mock the bot object and its methods
        # Since bot is now AsyncTeleBot, its methods will be awaitable.
        # We can use AsyncMock for methods like send_message, reply_to, etc.
        self.mock_bot_instance = MagicMock(spec=telebot.async_telebot.AsyncTeleBot)

        # Specific methods that are awaited need to be AsyncMock or return an awaitable
        self.mock_bot_instance.send_message = AsyncMock()
        self.mock_bot_instance.reply_to = AsyncMock()
        self.mock_bot_instance.edit_message_text = AsyncMock()
        self.mock_bot_instance.send_chat_action = AsyncMock()
        self.mock_bot_instance.get_file = AsyncMock()
        self.mock_bot_instance.download_file = AsyncMock()

        # Patch the bot instance within the 'bot' module
        self.bot_patcher = patch("bot.bot", self.mock_bot_instance)
        self.mock_bot_module_instance = (
            self.bot_patcher.start()
        )  # This is the bot instance used by the module

        # Mock datetime to control timestamps in filenames
        self.mock_datetime_patcher = patch("bot.datetime")
        self.mock_datetime = self.mock_datetime_patcher.start()
        self.mock_datetime.utcnow.return_value.strftime.return_value = (
            "YYYYMMDD_HHMMSS_ffffff"
        )

        # Patch log_local_bot_event
        self.mock_log_event_patcher = patch("bot.log_local_bot_event")
        self.mock_log_local_bot_event = self.mock_log_event_patcher.start()

        # Patch for OPENAI_API_KEY
        self.openai_api_key_patcher = patch("bot.OPENAI_API_KEY", "test_openai_key")
        self.mock_openai_api_key = self.openai_api_key_patcher.start()

        # Patch for openai.Audio.transcribe
        self.openai_transcribe_patcher = patch("openai.Audio.transcribe")
        self.mock_openai_transcribe = self.openai_transcribe_patcher.start()

        # Patch for bot.get_text_from_voice - will be started selectively in tests for handle_voice_message
        # It's an async function, so patch with AsyncMock if creating a mock instance directly.
        # If just patching the path, the test method will define its return_value or side_effect.
        self.get_text_from_voice_patcher = patch(
            "bot.get_text_from_voice", new_callable=AsyncMock
        )
        self.mock_get_text_from_voice = (
            None  # Will be set when patcher is started by calling .start()
        )

        # Patch for bot.handle_text_message - To be applied selectively if a test needs it as a mock
        # self.handle_text_message_patcher = patch('bot.handle_text_message')
        # self.mock_handle_text_message = None # Will be set if patcher is started

        # Patch for openai.ChatCompletion.create
        self.openai_chat_completion_patcher = patch("openai.ChatCompletion.create")
        self.mock_openai_chat_completion_create = (
            self.openai_chat_completion_patcher.start()
        )

        # Patch for os.remove
        self.os_remove_patcher = patch("os.remove")
        self.mock_os_remove = self.os_remove_patcher.start()

        # Patch for Path.exists
        self.path_exists_patcher = patch("pathlib.Path.exists")
        self.mock_path_exists = self.path_exists_patcher.start()
        self.mock_path_exists.return_value = (
            True  # Assume file exists for cleanup by default
        )

        # Temporary directory for voice files
        self.test_voice_file_dir = Path("test_voice_temp_dir")
        self.test_voice_file_dir.mkdir(parents=True, exist_ok=True)
        self.voice_file_dir_patcher = patch(
            "bot.VOICE_FILE_DIR", self.test_voice_file_dir
        )
        self.voice_file_dir_patcher.start()

    def tearDown(self):
        # Stop patchers
        self.bot_patcher.stop()
        self.mock_datetime_patcher.stop()
        self.mock_log_event_patcher.stop()
        self.openai_api_key_patcher.stop()
        self.openai_transcribe_patcher.stop()
        self.openai_chat_completion_patcher.stop()  # Stop the new patcher
        # Stop get_text_from_voice_patcher only if it was started
        if self.mock_get_text_from_voice is not None:  # Check if it was started
            try:
                self.get_text_from_voice_patcher.stop()
            except RuntimeError:  # Already stopped or not started
                pass
        # Stop handle_text_message_patcher only if it was started (currently it's not started in setUp)
        # if hasattr(self, 'handle_text_message_patcher') and self.handle_text_message_patcher.is_started:
        #     self.handle_text_message_patcher.stop()
        self.os_remove_patcher.stop()
        self.path_exists_patcher.stop()
        self.voice_file_dir_patcher.stop()

        # Clean up: remove dummy directory and its contents
        if self.test_commands_dir.exists():
            try:
                shutil.rmtree(
                    self.test_commands_dir
                )  # shutil.rmtree is more robust for non-empty dirs
            except FileNotFoundError:
                pass  # Already deleted or never created
        if self.test_voice_file_dir.exists():
            try:
                shutil.rmtree(self.test_voice_file_dir)
            except FileNotFoundError:
                pass  # Already deleted or never created

        # Restore original
        # There was a duplicate rmtree here, removing it.
        # bot.COMMAND_FILE_DIR should be restored.
        bot.COMMAND_FILE_DIR = self.original_command_file_dir
        bot.active_gpt_streams.clear()  # Clear active streams after each test

    def _create_mock_message(self, text_payload):
        mock_message = MagicMock(spec=telebot.types.Message)  # Add spec
        mock_message.chat = MagicMock(spec=telebot.types.Chat)  # Add spec
        mock_message.chat.id = 12345
        mock_message.text = (
            json.dumps(text_payload) if isinstance(text_payload, dict) else text_payload
        )
        return mock_message

    # --- Test Command Validation ---
    async def test_valid_command_gets_saved(self):  # Async
        command = {
            "type": "test_type",
            "module": "test_module",
            "args": {},
            "id": "test_id",
        }
        mock_message = self._create_mock_message(command)

        # Ensure this path is taken (not NLP, is JSON)
        with patch("bot.interpret", return_value=None):
            await bot.process_user_message(
                mock_message.chat.id, mock_message.text, mock_message
            )  # Await

        # Check file creation
        expected_module_dir = self.test_commands_dir / "telegram_mod_test_module"
        self.assertTrue(expected_module_dir.exists())

        expected_filename = f"YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
        expected_file_path = expected_module_dir / expected_filename
        self.assertTrue(expected_file_path.exists())

        with open(expected_file_path, "r") as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data, command)

        # Check reply
        self.mock_bot_module_instance.reply_to.assert_called_once()
        args, kwargs = self.mock_bot_module_instance.reply_to.call_args
        self.assertEqual(args[0], mock_message)
        self.assertTrue(args[1].startswith("✅ Command received and saved as"))
        self.assertIn(str(expected_file_path), args[1])

        # Check logging for successfully validated command
        found_log = False
        for call_arg in self.mock_log_local_bot_event.call_args_list:
            args, _ = call_arg
            if (
                f"Successfully validated JSON command from {mock_message.chat.id}: {json.dumps(command)}"
                in args[0]
            ):
                found_log = True
                break
        self.assertTrue(
            found_log,
            "Expected log for successful validation with full command data was not found.",
        )

    async def test_text_not_nlp_or_json_goes_to_katana_agent(
        self,
    ):  # Renamed and made async
        mock_message = self._create_mock_message("this is plain text, not a command")

        with patch("bot.interpret", return_value=None), patch(
            "bot.katana_agent_instance.get_response", return_value="Katana says hi"
        ) as mock_get_response:
            await bot.process_user_message(
                mock_message.chat.id, mock_message.text, mock_message
            )

        mock_get_response.assert_called_once()
        self.mock_bot_instance.reply_to.assert_called_once_with(
            mock_message, "Katana says hi"
        )

    async def test_missing_type_field(self):  # Async
        command = {
            "module": "test_module",
            "args": {},
            "id": "test_id",
        }  # type is missing
        mock_message = self._create_mock_message(command)
        with patch("bot.interpret", return_value=None):
            await bot.process_user_message(
                mock_message.chat.id, mock_message.text, mock_message
            )
        self.mock_bot_instance.reply_to.assert_called_with(
            mock_message, "Error: Missing required field 'type'."
        )

    # --- Passive Mode and /katana command tests ---
    async def test_katana_listen_enables_passive_mode(self):
        self.assertFalse(bot.katana_passive_mode)
        mock_message = self._create_mock_message("/katana listen")
        await bot.command_katana_impl(mock_message)
        self.assertTrue(bot.katana_passive_mode)
        self.mock_bot_instance.reply_to.assert_called_with(
            mock_message, "Катана слушает... 👂"
        )

    async def test_katana_stop_disables_passive_mode(self):
        bot.katana_passive_mode = True
        mock_message = self._create_mock_message("/katana stop")
        await bot.command_katana_impl(mock_message)
        self.assertFalse(bot.katana_passive_mode)
        self.mock_bot_instance.reply_to.assert_called_with(
            mock_message, "Катана больше не слушает. 🛑"
        )

    async def test_message_ignored_in_passive_mode(self):
        bot.katana_passive_mode = True
        mock_message = self._create_mock_message("any message")
        with patch("bot.interpret", new_callable=MagicMock) as mock_interpret:
            await bot.process_user_message(
                mock_message.chat.id, mock_message.text, mock_message
            )
            mock_interpret.assert_not_called()
            self.mock_bot_instance.reply_to.assert_not_called()

    async def test_katana_command_processed_in_passive_mode(self):
        bot.katana_passive_mode = True
        mock_message = self._create_mock_message("/katana stop")
        # We test the command impl directly, but process_user_message should let it through
        await bot.process_user_message(
            mock_message.chat.id, mock_message.text, mock_message
        )
        self.assertFalse(bot.katana_passive_mode)
        # The reply is from command_katana_impl, which is called by the handler, not process_user_message
        # This test should check that process_user_message doesn't block it.
        # A better test would be to mock the command handler and see if it's called.
        # For now, we assume the routing works and check the side effect.
        self.mock_bot_instance.reply_to.assert_called_with(
            mock_message, "Катана больше не слушает. 🛑"
        )

    # --- command_type routing tests ---
    async def test_command_type_info(self):
        command = {
            "type": "info",
            "module": "test",
            "args": {"text": "Hello Info"},
            "id": "info1",
        }
        mock_message = self._create_mock_message(command)
        with patch("bot.interpret", return_value=json.dumps(command)):
            await bot.process_user_message(
                mock_message.chat.id, mock_message.text, mock_message
            )
        self.mock_bot_instance.reply_to.assert_called_with(mock_message, "ℹ️ Hello Info")

    async def test_command_type_exec(self):
        command = {
            "type": "exec",
            "module": "test",
            "args": {"command": "echo 'hello'"},
            "id": "exec1",
        }
        mock_message = self._create_mock_message(command)
        with patch(
            "bot.run_katana_command", new_callable=AsyncMock, return_value="hello"
        ) as mock_run_command:
            await bot.process_user_message(
                mock_message.chat.id, json.dumps(command), mock_message
            )
        mock_run_command.assert_called_with("echo 'hello'")
        self.mock_bot_instance.reply_to.assert_called_with(
            mock_message, "⚙️ Executing: `echo 'hello'`\n\nhello", parse_mode="Markdown"
        )


if __name__ == "__main__":
    unittest.main()
