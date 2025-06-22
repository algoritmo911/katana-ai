import unittest
from unittest.mock import patch, MagicMock, mock_open, call
import json
import os
from importlib import reload # To re-import katana_bot for token testing

# from importlib import reload # Not using reload anymore, but import_module
import importlib # For import_module

# Ensures that the root of the project (the parent directory of 'bot') is in sys.path
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# DO NOT import bot.katana_bot here initially.
# It will be imported freshly in TestKatanaBot.setUp under patches.
# For TestKatanaBotTokenValidation, it will also manage its own imports.

# Global mock definitions for TeleBot part (used by TestKatanaBot.setUp)
mock_telebot_instance = MagicMock()
mock_telebot_class = MagicMock(return_value=mock_telebot_instance)
# mock_get_katana_response is no longer global for TestKatanaBot; it's created by patch.


class TestKatanaBot(unittest.TestCase):

    def setUp(self):
        # Reset the global TeleBot mocks
        mock_telebot_instance.reset_mock()
        mock_telebot_class.return_value = mock_telebot_instance

        # Apply patches and then import the module fresh
        self.patch_env = patch.dict(os.environ, {"KATANA_TELEGRAM_TOKEN": "123456:ABCDEF"}, clear=True)
        self.patch_telebot = patch('bot.katana_bot.telebot.TeleBot', mock_telebot_class)

        # Let patch create the mock for get_katana_response
        self.patch_get_katana_creator = patch('bot.katana_bot.get_katana_response')

        self.patch_env.start()
        self.patch_telebot.start()
        # Start the creator patch; it returns the mock it installed. This mock is specific to this test run.
        self.mock_get_katana_for_test = self.patch_get_katana_creator.start()

        self.addCleanup(self.patch_get_katana_creator.stop) # Stop in reverse order
        self.addCleanup(self.patch_telebot.stop)
        self.addCleanup(self.patch_env.stop)

        # Configure the mock created by patch for get_katana_response
        self.mock_get_katana_for_test.reset_mock() # Should be fresh, but good practice
        self.mock_get_katana_for_test.return_value = "Default via patch-created mock"
        self.mock_get_katana_for_test.side_effect = None

        # Force re-import by removing from sys.modules first, then importing.
        if 'bot.katana_bot' in sys.modules:
            del sys.modules['bot.katana_bot']
        self.bot_module = importlib.import_module('bot.katana_bot')

        self.bot_instance = self.bot_module.bot

        # Sanity checks
        if self.bot_instance != mock_telebot_instance:
            raise Exception(f"self.bot_instance (id: {id(self.bot_instance)}) is not mock_telebot_instance (id: {id(mock_telebot_instance)}). TeleBot Patching failed.")

        if self.bot_module.get_katana_response != self.mock_get_katana_for_test:
             raise Exception(f"self.bot_module.get_katana_response (id: {id(self.bot_module.get_katana_response)}) is not self.mock_get_katana_for_test (id: {id(self.mock_get_katana_for_test)}). Patching get_katana_response failed.")

        self.bot_module.katana_states.clear()

        # Common message object
        self.message = MagicMock()
        self.message.chat.id = 123
        self.message.from_user.username = "testuser"

    def test_handle_start(self):
        self.message.text = "/start"
        self.bot_module.handle_start(self.message)

        expected_reply = "Привет! Я — Katana. Готов к диалогу или JSON-команде."
        # Assert on the globally defined mock_telebot_instance which should be self.bot_instance
        mock_telebot_instance.reply_to.assert_called_once_with(self.message, expected_reply)

        self.assertIn(self.message.chat.id, self.bot_module.katana_states)
        expected_history_entry = {"role": self.bot_module.MESSAGE_ROLE_ASSISTANT, "content": expected_reply}
        self.assertIn(expected_history_entry, self.bot_module.katana_states[self.message.chat.id])

    def test_natural_language_message_success(self):
        self.message.text = "Привет, Катана!"
        specific_response = "Привет! Как я могу помочь?"
        self.mock_get_katana_for_test.return_value = specific_response # Use instance mock

        self.bot_module.handle_message_impl(self.message)

        expected_user_msg = {"role": self.bot_module.MESSAGE_ROLE_USER, "content": self.message.text}
        self.assertIn(expected_user_msg, self.bot_module.katana_states[self.message.chat.id])

        self.mock_get_katana_for_test.assert_called_once_with(self.bot_module.katana_states[self.message.chat.id])

        mock_telebot_instance.reply_to.assert_called_once_with(self.message, specific_response)

        expected_assistant_msg = {"role": self.bot_module.MESSAGE_ROLE_ASSISTANT, "content": specific_response}
        self.assertIn(expected_assistant_msg, self.bot_module.katana_states[self.message.chat.id])
        self.assertEqual(len(self.bot_module.katana_states[self.message.chat.id]), 2)

    @patch('bot.katana_bot.logger')
    def test_get_katana_response_exception(self, mock_logger_in_test): # Renamed to avoid clash if logger is used in setUp
        self.message.text = "Вызови ошибку"
        test_exception = Exception("Test NLP error")
        self.mock_get_katana_for_test.side_effect = test_exception # Use instance mock

        self.bot_module.handle_message_impl(self.message)

        expected_user_msg = {"role": self.bot_module.MESSAGE_ROLE_USER, "content": self.message.text}
        self.assertIn(expected_user_msg, self.bot_module.katana_states[self.message.chat.id])

        self.mock_get_katana_for_test.assert_called_once_with(self.bot_module.katana_states[self.message.chat.id])

        self.assertTrue(mock_logger_in_test.error.called)
        args, kwargs = mock_logger_in_test.error.call_args
        self.assertIn("Error during get_katana_response or reply", args[0])
        self.assertIn("Test NLP error", args[0])
        self.assertTrue(kwargs.get('exc_info'))

        self.assertTrue(mock_telebot_instance.reply_to.called) # Check the global instance
        reply_args, _ = mock_telebot_instance.reply_to.call_args
        self.assertIn("Произошла внутренняя ошибка", reply_args[1])
        self.assertIn("Код ошибки:", reply_args[1])

        self.assertEqual(len(self.bot_module.katana_states[self.message.chat.id]), 1)

    def test_json_command_log_event(self):
        command = {"type": "log_event", "module": "test_mod", "args": {"data": "test"}, "id": "123cmd"}
        self.message.text = json.dumps(command)

        self.bot_module.handle_message_impl(self.message)

        expected_reply = "✅ 'log_event' обработан (заглушка)."
        mock_telebot_instance.reply_to.assert_called_once_with(self.message, expected_reply)

        history = self.bot_module.katana_states[self.message.chat.id]
        self.assertEqual(history[0], {"role": self.bot_module.MESSAGE_ROLE_USER, "content": self.message.text})
        self.assertEqual(history[1], {"role": self.bot_module.MESSAGE_ROLE_ASSISTANT, "content": expected_reply})

    def test_json_command_mind_clearing(self):
        self.bot_module.katana_states[self.message.chat.id] = [{"role": "user", "content": "Old message"}]

        command = {"type": "mind_clearing", "module": "test_mod", "args": {}, "id": "124cmd"}
        self.message.text = json.dumps(command)

        self.bot_module.handle_message_impl(self.message)

        expected_reply = "✅ Контекст диалога очищен. Начинаем с чистого листа."
        mock_telebot_instance.reply_to.assert_called_once_with(self.message, expected_reply)

        history = self.bot_module.katana_states[self.message.chat.id]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0], {"role": self.bot_module.MESSAGE_ROLE_ASSISTANT, "content": expected_reply})

    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    @patch('bot.katana_bot.Path.mkdir')
    def test_json_command_generic_save(self, mock_mkdir, mock_json_dump, mock_file_open):
        command = {"type": "generic_command", "module": "test_module", "args": {"key": "value"}, "id": "125cmd"}
        self.message.text = json.dumps(command)

        self.bot_module.handle_message_impl(self.message)

        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        self.assertTrue(mock_file_open.called)
        opened_filepath_str = mock_file_open.call_args[0][0]
        self.assertIn(f"_{self.message.chat.id}.json", str(opened_filepath_str))
        self.assertIn(f"telegram_mod_{command['module']}", str(opened_filepath_str))

        mock_json_dump.assert_called_once_with(command, mock_file_open(), ensure_ascii=False, indent=2)

        expected_reply_fragment = "Команда принята и сохранена как"
        self.assertTrue(mock_telebot_instance.reply_to.called)
        reply_args, _ = mock_telebot_instance.reply_to.call_args
        self.assertIn(expected_reply_fragment, reply_args[1])

        history = self.bot_module.katana_states[self.message.chat.id]
        self.assertEqual(history[0], {"role": self.bot_module.MESSAGE_ROLE_USER, "content": self.message.text})
        self.assertTrue(history[1]["content"].startswith("✅ Команда принята"))

    def test_json_invalid_structure_treated_as_natural_language(self):
        invalid_command_json = {"type": "some_type", "args": {}, "id": "126"}
        self.message.text = json.dumps(invalid_command_json)

        specific_nlp_response = "Tratado como NL."
        mock_get_katana_response.return_value = specific_nlp_response

        self.bot_module.handle_message_impl(self.message)

        mock_get_katana_response.assert_called_once()
        mock_telebot_instance.reply_to.assert_called_once_with(self.message, specific_nlp_response)

        history = self.bot_module.katana_states[self.message.chat.id]
        self.assertEqual(history[0], {"role": self.bot_module.MESSAGE_ROLE_USER, "content": self.message.text})
        self.assertEqual(history[1], {"role": self.bot_module.MESSAGE_ROLE_ASSISTANT, "content": specific_nlp_response})


class TestKatanaBotTokenValidation(unittest.TestCase):

    def import_katana_bot_fresh_under_patches(self):
        # This helper will import katana_bot ensuring it's done with specific patches for TeleBot,
        # primarily to check os.environ effects without full NLP/TeleBot functionality.
        # The mock_telebot_class_for_validator is specific to this test class if needed,
        # or we can use the global one if its state is simple (just returns a MagicMock).
        # For these tests, we mainly care that TeleBot() doesn't error if token is valid,
        # or that the module load errors out before TeleBot() is even called if token is invalid.

        # Use a local mock for TeleBot just for this validation context if needed,
        # or rely on the global mock_telebot_class if its use here is okay.
        # Let's use a local one to be safe and explicit for this test class.
        local_mock_telebot_instance = MagicMock(name="LocalTeleBotInstanceForTokenValidation")
        local_mock_telebot_class = MagicMock(name="LocalTeleBotClassForTokenValidation", return_value=local_mock_telebot_instance)

        with patch('bot.katana_bot.telebot.TeleBot', local_mock_telebot_class) as validator_telebot_patch_obj:
            if 'bot.katana_bot' in sys.modules:
                del sys.modules['bot.katana_bot']
            module = importlib.import_module('bot.katana_bot')
            # Return the mock class used, so we can assert calls on it.
            return module, validator_telebot_patch_obj

    @patch.dict(os.environ, {}, clear=True)
    # No need to patch TeleBot here if import_katana_bot_fresh_under_patches does it.
    def test_missing_token(self):
        with self.assertRaisesRegex(ValueError, "Invalid or missing Telegram API token"):
            # The import_katana_bot_fresh_under_patches will apply its own TeleBot patch,
            # but the error should occur before TeleBot is even called.
            self.import_katana_bot_fresh_under_patches()


    @patch.dict(os.environ, {"KATANA_TELEGRAM_TOKEN": "INVALID_TOKEN_NO_COLON"}, clear=True)
    def test_invalid_format_token(self):
        with self.assertRaisesRegex(ValueError, "Invalid or missing Telegram API token"):
            self.import_katana_bot_fresh_under_patches()

    @patch.dict(os.environ, {"KATANA_TELEGRAM_TOKEN": "123456:ABCDEF"}, clear=True)
    def test_valid_token(self):
        try:
            # We need the mock_telebot_cls that was used by import_katana_bot_fresh_under_patches
            _, mock_used_by_import = self.import_katana_bot_fresh_under_patches()
            mock_used_by_import.assert_called_with("123456:ABCDEF")
        except ValueError:
            self.fail("Valid token raised ValueError during module load")


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

# Removed the sys.path.pop(0) at the end of the file.
# If PROJECT_ROOT was added to sys.path, it will persist for the test session.
# This is generally fine for `python -m unittest` runs.
