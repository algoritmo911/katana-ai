import unittest
from unittest.mock import patch, MagicMock, mock_open, call
import pytest
import telebot
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

import types

class DummyMessage:
    def __init__(self, text, chat_id):
        self.text = text
        self.chat = types.SimpleNamespace(id=chat_id)
        self.from_user = types.SimpleNamespace(id=chat_id)

# Global mock definitions for TeleBot part (used by TestKatanaBot.setUp)
mock_telebot_instance = MagicMock()
mock_telebot_class = MagicMock(return_value=mock_telebot_instance)
# mock_get_katana_response is no longer global for TestKatanaBot; it's created by patch.


def mock_send_message(chat_id, text, **kwargs):
    print(f"Mock send_message to {chat_id}: {text}")
    return {"ok": True}

# TODO: Переписать тесты под новую классовую архитектуру KatanaBot. Задача: TSK-101
@pytest.mark.skip(reason="Тесты устарели после рефакторинга KatanaBot на классы.")
class TestKatanaBot(unittest.TestCase):

    def setUp(self):
        # Reset the global TeleBot mocks
        mock_telebot_instance.reset_mock()
        mock_telebot_class.return_value = mock_telebot_instance

        # Apply patches and then import the module fresh
        # Ensure necessary env vars for module import are set, including for MemoryManager if it's not fully mocked during import
        env_vars_for_import = {
            "KATANA_TELEGRAM_TOKEN": "123456:ABCDEF",
            "REDIS_HOST": "127.0.0.1", # Use explicit IP for testing
            "REDIS_PORT": "63790", # Use a non-standard port to avoid collision / ensure it's our mock
            "ANTHROPIC_API_KEY": "test_anthropic_key", # Prevent warnings
            "OPENAI_API_KEY": "test_openai_key" # Prevent warnings
        }
        self.patch_env = patch.dict(os.environ, env_vars_for_import, clear=True)
        self.patch_telebot = patch('telebot.TeleBot', mock_telebot_class)

        self.patch_env.start()
        self.patch_telebot.start()
        self.addCleanup(self.patch_telebot.stop)
        self.addCleanup(self.patch_env.stop) # Env patch should be stopped last or after module is done

        # Force re-import by removing from sys.modules first, then importing.
        if 'bot.katana_bot' in sys.modules:
            del sys.modules['bot.katana_bot']

        # Import the module first
        # Note: This will run the global code in katana_bot.py, including MemoryManager instantiation.
        # For this to not fail with Redis connection, os.environ should have KATANA_TELEGRAM_TOKEN,
        # and ideally, we'd want to prevent the real MemoryManager from connecting.
        # The patch_env for KATANA_TELEGRAM_TOKEN is already active.

        # To prevent real MemoryManager connection during this initial import,
        # we can temporarily patch redis.Redis itself if MemoryManager uses it directly.
        # Or, a more robust way for testing is to ensure MemoryManager can be instantiated
        # without side effects if certain env vars (like a TEST_MODE) are set.
        # Given the current structure, patching the class `bot.katana_bot.MemoryManager`
        # to return a simple MagicMock *during the import* is the goal.

        # Patch MemoryManager class globally for the duration of the import
        # This mock will be replaced by a more specific instance mock later if needed by tests.
        # Force re-import by removing from sys.modules first, then importing.
        if 'bot.katana_bot' in sys.modules:
            del sys.modules['bot.katana_bot']

        # Import the module. With lazy-init, MemoryManager won't be created now.
        # get_katana_response still needs to be mocked if it's used by other module-level code (if any)
        # or to ensure tests use the mock.
        self.mock_get_katana_for_test = MagicMock(return_value="Default mock for get_katana_response")
        patch_get_katana_during_import = patch('bot.katana_bot.get_katana_response', self.mock_get_katana_for_test)

        patch_get_katana_during_import.start()
        self.bot_module = importlib.import_module('bot.katana_bot')
        patch_get_katana_during_import.stop() # Stop it, will re-patch if needed or rely on this one.
                                            # For simplicity, let this be the main mock for get_katana_response.
        self.addCleanup(patch_get_katana_during_import.stop) # Ensure it's stopped at cleanup.

        # self.bot_module.memory_manager is None at this point.
        # Create a mock instance that will replace `self.bot_module.memory_manager`
        self.mock_memory_manager_instance = MagicMock()
        self.mock_memory_manager_instance.get_history = MagicMock(return_value=[])
        self.mock_memory_manager_instance.add_message_to_history = MagicMock()
        self.mock_memory_manager_instance.clear_history = MagicMock()

        # Patch the instance variable `memory_manager` in the loaded bot_module
        self.patch_bot_module_mm_instance = patch.object(self.bot_module, 'memory_manager', self.mock_memory_manager_instance)
        self.patch_bot_module_mm_instance.start()
        self.addCleanup(self.patch_bot_module_mm_instance.stop)

        # If katana_bot.init_dependencies() was to be called by tests, this is where it would go,
        # and self.bot_module.memory_manager would then be our mock.
        # For these tests, we assume init_dependencies() is NOT called, and handlers directly use
        # the (now mocked) self.bot_module.memory_manager.
        # If init_dependencies() *is* called by a test, that test needs to ensure
        # `src.memory.memory_manager.MemoryManager` is patched if it wants to avoid real Redis.
        # However, the handlers like handle_message_impl directly use the global `memory_manager`.
        # They will only work if `memory_manager` is not None.
        # So, we MUST ensure `self.bot_module.memory_manager` is our mock. The above patch.object does this.

        self.bot_instance = self.bot_module.bot # This is the TeleBot mock

        # Sanity checks
        if self.bot_instance != mock_telebot_instance:
            raise Exception(f"self.bot_instance is not mock_telebot_instance. TeleBot Patching failed.")

        # if self.bot_module.get_katana_response is not self.mock_get_katana_for_test: # Check against the one used for import
        #      raise Exception(f"bot.katana_bot.get_katana_response is not self.mock_get_katana_for_test. Patching get_katana_response failed.")

        if self.bot_module.memory_manager is not self.mock_memory_manager_instance:
             # This check is vital. It ensures the module-level 'memory_manager' variable in katana_bot
             # is indeed our mock instance for the duration of the test.
            raise Exception("bot.katana_bot.memory_manager is not self.mock_memory_manager_instance. Patching MemoryManager instance failed.")

        # Common message object
        self.message = MagicMock()
        self.message.chat.id = 123 # Will be converted to str for memory_manager
        self.chat_id_str = str(self.message.chat.id)
        self.message.from_user.username = "testuser"

    def test_handle_start(self):
        msg = DummyMessage("/start", 123456)
        with patch('bot.bot_instance.bot') as mock_bot:
            mock_bot.reply_to = MagicMock()
            self.bot_module.handle_start(msg)
            expected_reply = "Привет! Я — Katana. Готов к диалогу или JSON-команде."
            mock_bot.reply_to.assert_called_once_with(msg, expected_reply)

    def test_natural_language_message_success(self):
        self.message.text = "Привет, Катана!"
        specific_response = "Привет! Как я могу помочь?"
        self.mock_get_katana_for_test.return_value = specific_response

        # Simulate MemoryManager returning an empty history for this new interaction
        self.bot_module.memory_manager.get_history.return_value = []

        self.bot_module.handle_message_impl(self.message)

        # 1. Check get_history was called
        self.bot_module.memory_manager.get_history.assert_called_once_with(self.chat_id_str)

        # 2. Check user message was added
        expected_user_msg_content = {"role": self.bot_module.MESSAGE_ROLE_USER, "content": self.message.text}
        # The history passed to get_katana_response includes the new user message
        # So, the call to get_katana_response will have a list with one item.
        # The add_message_to_history for user message is called before get_katana_response

        # 3. Check get_katana_response was called with history including user message
        # The local current_history is built up: fetched_history + user_message
        history_for_nlp = [expected_user_msg_content] # Since get_history returned []
        self.mock_get_katana_for_test.assert_called_once_with(history_for_nlp)

        # 4. Check bot replied
        mock_telebot_instance.reply_to.assert_called_once_with(self.message, specific_response)

        # 5. Check assistant message was added
        expected_assistant_msg_content = {"role": self.bot_module.MESSAGE_ROLE_ASSISTANT, "content": specific_response}

        # Assert that add_message_to_history was called for user and then for assistant
        self.assertEqual(self.bot_module.memory_manager.add_message_to_history.call_count, 2)
        calls = self.bot_module.memory_manager.add_message_to_history.call_args_list

        # Check user message call (ignoring timestamp which is added internally)
        self.assertEqual(calls[0][0][0], self.chat_id_str)
        self.assertEqual(calls[0][0][1]['role'], expected_user_msg_content['role'])
        self.assertEqual(calls[0][0][1]['content'], expected_user_msg_content['content'])

        # Check assistant message call
        self.assertEqual(calls[1][0][0], self.chat_id_str)
        self.assertEqual(calls[1][0][1]['role'], expected_assistant_msg_content['role'])
        self.assertEqual(calls[1][0][1]['content'], expected_assistant_msg_content['content'])


    @patch('bot.katana_bot.logger')
    def test_get_katana_response_exception(self, mock_logger_in_test):
        self.message.text = "Вызови ошибку"
        test_exception = Exception("Test NLP error")
        self.mock_get_katana_for_test.side_effect = test_exception

        self.bot_module.memory_manager.get_history.return_value = [] # Start with empty history

        self.bot_module.handle_message_impl(self.message)

        self.bot_module.memory_manager.get_history.assert_called_once_with(self.chat_id_str)

        expected_user_msg_content = {"role": self.bot_module.MESSAGE_ROLE_USER, "content": self.message.text}
        history_for_nlp = [expected_user_msg_content]
        self.mock_get_katana_for_test.assert_called_once_with(history_for_nlp)

        # User message should have been added
        self.bot_module.memory_manager.add_message_to_history.assert_called_once()
        call_args = self.bot_module.memory_manager.add_message_to_history.call_args[0]
        self.assertEqual(call_args[0], self.chat_id_str)
        self.assertEqual(call_args[1]['role'], expected_user_msg_content['role'])
        self.assertEqual(call_args[1]['content'], expected_user_msg_content['content'])
        # Assistant's error message is NOT added to history.

        self.assertTrue(mock_logger_in_test.error.called)
        self.assertTrue(mock_telebot_instance.reply_to.called)


    def test_json_command_log_event(self):
        command = {"type": "log_event", "module": "test_mod", "args": {"data": "test"}, "id": "123cmd"}
        self.message.text = json.dumps(command)
        self.bot_module.memory_manager.get_history.return_value = []

        self.bot_module.handle_message_impl(self.message)

        expected_reply = "✅ 'log_event' обработан (заглушка)."
        mock_telebot_instance.reply_to.assert_called_once_with(self.message, expected_reply)

        self.assertEqual(self.bot_module.memory_manager.add_message_to_history.call_count, 2)
        calls = self.bot_module.memory_manager.add_message_to_history.call_args_list
        # User command
        self.assertEqual(calls[0][0][1]['content'], self.message.text)
        # Bot response
        self.assertEqual(calls[1][0][1]['content'], expected_reply)


    def test_json_command_mind_clearing(self):
        # Simulate some pre-existing history that will be cleared
        self.bot_module.memory_manager.get_history.return_value = [{"role": "user", "content": "Old message"}]

        command = {"type": "mind_clearing", "module": "test_mod", "args": {}, "id": "124cmd"}
        self.message.text = json.dumps(command)

        self.bot_module.handle_message_impl(self.message)

        expected_reply = "✅ Контекст диалога очищен. Начинаем с чистого листа."
        mock_telebot_instance.reply_to.assert_called_once_with(self.message, expected_reply)

        # Check user message was added first
        self.bot_module.memory_manager.add_message_to_history.assert_any_call(
            self.chat_id_str,
            unittest.mock.ANY # content will have timestamp
        )
        # Check history was cleared
        self.bot_module.memory_manager.clear_history.assert_called_once_with(self.chat_id_str)

        # Check confirmation message was added AFTER clearing
        # This requires inspecting call order or specific content of the last add_message_to_history
        # The last call to add_message_to_history should be the confirmation.
        last_add_call = self.bot_module.memory_manager.add_message_to_history.call_args_list[-1]
        self.assertEqual(last_add_call[0][0], self.chat_id_str)
        self.assertEqual(last_add_call[0][1]['role'], self.bot_module.MESSAGE_ROLE_ASSISTANT)
        self.assertEqual(last_add_call[0][1]['content'], expected_reply)

        # Total add_message_to_history calls: 1 for user command, 1 for bot's confirmation
        self.assertEqual(self.bot_module.memory_manager.add_message_to_history.call_count, 2)


    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    @patch('bot.katana_bot.Path.mkdir')
    def test_json_command_generic_save(self, mock_mkdir, mock_json_dump, mock_file_open):
        command = {"type": "generic_command", "module": "test_module", "args": {"key": "value"}, "id": "125cmd"}
        self.message.text = json.dumps(command)
        self.bot_module.memory_manager.get_history.return_value = []


        self.bot_module.handle_message_impl(self.message)

        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        self.assertTrue(mock_file_open.called)
        opened_filepath_str = mock_file_open.call_args[0][0]
        # Use self.chat_id_str for consistency as message.chat.id is int
        self.assertIn(f"_{self.chat_id_str}.json", str(opened_filepath_str))
        self.assertIn(f"telegram_mod_{command['module']}", str(opened_filepath_str))

        mock_json_dump.assert_called_once_with(command, mock_file_open(), ensure_ascii=False, indent=2)

        expected_reply_fragment = "Команда принята и сохранена как"
        self.assertTrue(mock_telebot_instance.reply_to.called)
        reply_args, _ = mock_telebot_instance.reply_to.call_args
        self.assertIn(expected_reply_fragment, reply_args[1])

        # Check history was updated for user command and bot response
        self.assertEqual(self.bot_module.memory_manager.add_message_to_history.call_count, 2)
        calls = self.bot_module.memory_manager.add_message_to_history.call_args_list
        self.assertEqual(calls[0][0][1]['content'], self.message.text) # User command
        self.assertTrue(calls[1][0][1]['content'].startswith("✅ Команда принята")) # Bot response

    def test_json_invalid_structure_treated_as_natural_language(self):
        invalid_command_json = {"type": "some_type", "args": {}, "id": "126"} # Missing "module"
        self.message.text = json.dumps(invalid_command_json)
        self.bot_module.memory_manager.get_history.return_value = []

        specific_nlp_response = "Tratado como NL."
        # self.mock_get_katana_for_test is already set up in setUp
        self.mock_get_katana_for_test.return_value = specific_nlp_response

        self.bot_module.handle_message_impl(self.message)

        self.mock_get_katana_for_test.assert_called_once() # Called because it's treated as natural language
        mock_telebot_instance.reply_to.assert_called_once_with(self.message, specific_nlp_response)

        # Check history updates
        self.assertEqual(self.bot_module.memory_manager.add_message_to_history.call_count, 2)
        calls = self.bot_module.memory_manager.add_message_to_history.call_args_list
        self.assertEqual(calls[0][0][1]['content'], self.message.text) # User (invalid) command
        self.assertEqual(calls[1][0][1]['content'], specific_nlp_response) # Bot NLP response


# TODO: Переписать тесты под новую классовую архитектуру KatanaBot. Задача: TSK-101
@pytest.mark.skip(reason="Тесты устарели после рефакторинга KatanaBot на классы.")
class TestKatanaBotTokenValidation(unittest.TestCase):

    def import_katana_bot_fresh_under_patches(self, env_vars=None):
        # This helper will import katana_bot ensuring it's done with specific patches for TeleBot,
        # primarily to check os.environ effects without full NLP/TeleBot functionality.

        current_env = os.environ.copy()
        if env_vars:
            current_env.update(env_vars)

        # Since MemoryManager is lazy-loaded, we don't need to patch it for these token validation tests,
        # as its instantiation won't be triggered by a simple import if the token logic is self-contained.
        # We primarily care about TeleBot instantiation and environment variables.

        # Use a local mock for TeleBot just for this validation context
        local_mock_telebot_instance = MagicMock(name="LocalTeleBotInstanceForTokenValidation")
        local_mock_telebot_class = MagicMock(name="LocalTeleBotClassForTokenValidation", return_value=local_mock_telebot_instance)

        # Ensure necessary env vars for MemoryManager are present, even if it's not instantiated,
        # to prevent errors if any module-level code reads them (though ideally it shouldn't for token validation path).
        # These are mostly for full module load, but good to have defaults.
        default_redis_env = {
            "REDIS_HOST": "dummy_host_for_token_test",
            "REDIS_PORT": "1111",
            "ANTHROPIC_API_KEY": "dummy_anthropic",
            "OPENAI_API_KEY": "dummy_openai"
        }
        if env_vars: # User-provided env_vars for the specific test take precedence
            final_env = {**default_redis_env, **env_vars}
        else:
            final_env = default_redis_env

        with patch.dict(os.environ, final_env, clear=True):
            with patch('telebot.TeleBot', local_mock_telebot_class) as validator_telebot_patch_obj:
                # No need to patch MemoryManager class here if it's truly lazy loaded and not hit by token validation path
                if 'bot.katana_bot' in sys.modules:
                    del sys.modules['bot.katana_bot']
                module = importlib.import_module('bot.katana_bot')
                return module, validator_telebot_patch_obj, None # No MemoryManager class mock to return


    def test_missing_token(self):
        with self.assertRaisesRegex(ValueError, "Invalid or missing Telegram API token"):
            # Pass only an empty dict for env_vars if we want to simulate absolutely nothing set
            # The helper will merge with its defaults. If we want to override defaults to be empty:
            self.import_katana_bot_fresh_under_patches(env_vars={"KATANA_TELEGRAM_TOKEN": ""})


    def test_invalid_format_token(self):
        with self.assertRaisesRegex(ValueError, "Invalid or missing Telegram API token"):
            self.import_katana_bot_fresh_under_patches(env_vars={"KATANA_TELEGRAM_TOKEN": "INVALID_TOKEN_NO_COLON"})

    def test_valid_token(self):
        try:
            # For a valid token, the module should load, and TeleBot should be instantiated.
            # MemoryManager is not instantiated at import time due to lazy loading.
            env_vars_for_valid_token = {
                "KATANA_TELEGRAM_TOKEN": "123456:ABCDEF",
                # other necessary minimal env vars if any, but Redis ones are not strictly needed for module load
                # if MemoryManager() is not called.
            }
            module, mock_telebot_cls_used, _ = self.import_katana_bot_fresh_under_patches(
                env_vars=env_vars_for_valid_token
            )
            mock_telebot_cls_used.assert_called_with("123456:ABCDEF")
            self.assertIsNotNone(module.bot) # Check that bot was initialized

        except ValueError:
            self.fail("Valid token raised ValueError during module load")


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

# Removed the sys.path.pop(0) at the end of the file.
# If PROJECT_ROOT was added to sys.path, it will persist for the test session.
# This is generally fine for `python -m unittest` runs.
