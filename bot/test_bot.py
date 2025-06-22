import unittest
from unittest.mock import MagicMock, patch, call
import json
from pathlib import Path
import shutil # For robust directory removal
import copy # For deepcopying user_memory

# Assuming bot.py is in the same directory or accessible in PYTHONPATH
from bot import katana_bot # Corrected import
from bot.nlp import context as nlp_context # Import for initial context

class TestKatanaBotNLP(unittest.TestCase):

    def setUp(self):
        # Mock the bot object and its methods from telebot
        self.mock_telebot_instance = MagicMock()
        # Patching the bot instance directly in the imported katana_bot module
        self.telebot_patcher = patch('bot.katana_bot.bot', self.mock_telebot_instance)
        self.mock_telebot_instance_patched = self.telebot_patcher.start()

        # Store and clear user_memory for each test
        self.original_user_memory = copy.deepcopy(katana_bot.user_memory)
        katana_bot.user_memory.clear()

        # Mock datetime for consistent history timestamps if needed
        # Patching datetime directly in the imported katana_bot module
        self.mock_datetime_patcher = patch('bot.katana_bot.datetime')
        self.mock_datetime = self.mock_datetime_patcher.start()
        self.mock_datetime.utcnow.return_value.isoformat.return_value = "TEST_TIMESTAMP"
        self.mock_datetime.now.return_value.strftime.return_value = "TEST_TIME"


    def tearDown(self):
        self.telebot_patcher.stop()
        self.mock_datetime_patcher.stop()
        # Restore user_memory
        katana_bot.user_memory = self.original_user_memory


    def _create_mock_message(self, text_payload, chat_id=12345, content_type='text'):
        mock_message = MagicMock()
        mock_message.chat.id = chat_id
        mock_message.text = text_payload
        mock_message.content_type = content_type
        # For /start or /help commands
        if text_payload.startswith('/'):
            mock_message.entities = [MagicMock(type='bot_command', offset=0, length=len(text_payload))]
        else:
            mock_message.entities = None
        return mock_message

    def test_handle_start_initializes_memory_and_replies(self):
        mock_message = self._create_mock_message("/start")
        
        katana_bot.handle_start_help(mock_message)
        
        self.assertIn(mock_message.chat.id, katana_bot.user_memory)
        self.assertIn("context", katana_bot.user_memory[mock_message.chat.id])
        self.assertIn("history", katana_bot.user_memory[mock_message.chat.id])
        self.assertEqual(len(katana_bot.user_memory[mock_message.chat.id]["history"]), 0)
        
        self.mock_telebot_instance_patched.reply_to.assert_called_once()
        args, _ = self.mock_telebot_instance_patched.reply_to.call_args
        self.assertEqual(args[0], mock_message)
        self.assertTrue(args[1].startswith("Привет! Я Katana, ваш умный ассистент."))

    def test_simple_greeting_intent(self):
        chat_id = 100
        mock_message = self._create_mock_message("Привет", chat_id=chat_id)
        
        katana_bot.handle_user_chat_message(mock_message)
        
        self.mock_telebot_instance_patched.reply_to.assert_called_once()
        args, _ = self.mock_telebot_instance_patched.reply_to.call_args
        self.assertEqual(args[0], mock_message)
        self.assertIn(args[1], ["Привет!", "Здравствуйте!", "Рад вас снова видеть!"])

        self.assertIn(chat_id, katana_bot.user_memory)
        self.assertEqual(len(katana_bot.user_memory[chat_id]["history"]), 1)
        self.assertEqual(katana_bot.user_memory[chat_id]["history"][0]["user"], "Привет")
        self.assertEqual(katana_bot.user_memory[chat_id]["context"]["last_recognized_intent"], "greeting")

    def test_get_weather_with_city_intent(self):
        chat_id = 200
        mock_message = self._create_mock_message("какая погода в Москве", chat_id=chat_id)

        katana_bot.handle_user_chat_message(mock_message)

        self.mock_telebot_instance_patched.reply_to.assert_called_once()
        args, _ = self.mock_telebot_instance_patched.reply_to.call_args
        self.assertEqual(args[0], mock_message)
        # Гибкая проверка, т.к. город может быть в другом падеже ("Москве")
        self.assertTrue("Погода в городе Москв" in args[1] and "отличная!" in args[1])

        self.assertIn(chat_id, katana_bot.user_memory)
        self.assertEqual(katana_bot.user_memory[chat_id]["context"]["entities"].get("city"), "Москве") # Ожидаем извлечение в том падеже, как в тексте
        self.assertEqual(katana_bot.user_memory[chat_id]["context"]["last_processed_intent"], "get_weather")

    def test_get_weather_context_clarification(self):
        chat_id = 300
        # 1. User asks for weather without city
        mock_message1 = self._create_mock_message("какая погода?", chat_id=chat_id)
        katana_bot.handle_user_chat_message(mock_message1)

        self.mock_telebot_instance_patched.reply_to.assert_called_with(mock_message1, "Для какого города вы хотите узнать погоду?")
        self.assertEqual(katana_bot.user_memory[chat_id]["context"]["last_processed_intent"], "clarify_city_for_weather")

        # 2. User provides city
        mock_message2 = self._create_mock_message("в Казани", chat_id=chat_id)
        katana_bot.handle_user_chat_message(mock_message2)

        self.mock_telebot_instance_patched.reply_to.assert_called_with(mock_message2, "☀️ Погода в городе Казани отличная! (но это не точно)")
        self.assertEqual(katana_bot.user_memory[chat_id]["context"]["entities"].get("city"), "Казани")
        self.assertEqual(katana_bot.user_memory[chat_id]["context"]["last_processed_intent"], "get_weather")
        self.assertEqual(len(katana_bot.user_memory[chat_id]["history"]), 2)

    def test_multi_intent_greeting_and_joke(self):
        chat_id = 400
        mock_message = self._create_mock_message("Привет, расскажи анекдот", chat_id=chat_id)

        katana_bot.handle_user_chat_message(mock_message)

        self.mock_telebot_instance_patched.reply_to.assert_called_once()
        args, _ = self.mock_telebot_instance_patched.reply_to.call_args

        # Check that both responses are present
        self.assertTrue(any(greet_resp in args[1] for greet_resp in ["Привет!", "Здравствуйте!", "Рад вас снова видеть!"]))
        self.assertTrue(any(joke_resp in args[1] for joke_resp in ["Колобок повесился.", "Почему программисты предпочитают темную тему? Потому что свет притягивает баги!", "Заходит улитка в бар..."]))

        self.assertIn(chat_id, katana_bot.user_memory)
        # last_processed_intent might be one of them, depends on order in INTENT_HANDLERS or nlp_result.intents
        # Check that context has entities if any, and history is updated.
        # For this basic NLP, intent order is fixed by parser's keyword check order. greeting is usually first.
        self.assertIn(katana_bot.user_memory[chat_id]["context"]["last_processed_intent"], ["greeting", "tell_joke"])


    def test_fallback_intent(self):
        chat_id = 500
        mock_message = self._create_mock_message("абракадабра", chat_id=chat_id)
        
        katana_bot.handle_user_chat_message(mock_message)
        
        self.mock_telebot_instance_patched.reply_to.assert_called_once()
        args, _ = self.mock_telebot_instance_patched.reply_to.call_args
        self.assertIn(args[1], [
            "Я не совсем понял, что вы имеете в виду. Можете переформулировать?",
            "Хм, я пока не умею на это отвечать. Попробуйте что-нибудь другое.",
            "Извините, я не распознал вашу команду."
        ])
        self.assertEqual(katana_bot.user_memory[chat_id]["context"]["last_processed_intent"], "fallback")

    def test_history_is_saved_and_limited(self):
        chat_id = 600
        # Send 25 messages to test history limit (currently 20)
        for i in range(25):
            text = f"Сообщение номер {i+1}"
            mock_msg = self._create_mock_message(text, chat_id=chat_id)
            katana_bot.handle_user_chat_message(mock_msg) # Will mostly be fallback

        self.assertIn(chat_id, katana_bot.user_memory)
        self.assertEqual(len(katana_bot.user_memory[chat_id]["history"]), 20) # Check history limit
        self.assertEqual(katana_bot.user_memory[chat_id]["history"][0]["user"], "Сообщение номер 6") # Check first message after limit
        self.assertEqual(katana_bot.user_memory[chat_id]["history"][-1]["user"], "Сообщение номер 25") # Check last message

    def test_user_state_persistence_and_settings_field(self):
        chat_id = 777

        # 1. Initial message to create user state
        # Ensure user_memory for this chat_id is clean before starting
        if chat_id in katana_bot.user_memory:
            del katana_bot.user_memory[chat_id]

        mock_message1 = self._create_mock_message("Первое сообщение для состояния", chat_id=chat_id)
        # Patch nlp_parser.analyze_text for predictable output
        with patch('bot.katana_bot.nlp_parser.analyze_text') as mock_analyze:
            mock_analyze.return_value = {
                "intents": [{"name": "test_intent", "confidence": 1.0}],
                "entities": {"test_entity": "value1"},
                "original_text": "Первое сообщение для состояния"
            }
            katana_bot.handle_user_chat_message(mock_message1)

        # Check initial state includes settings
        self.assertIn(chat_id, katana_bot.user_memory)
        self.assertIn("settings", katana_bot.user_memory[chat_id])
        self.assertEqual(katana_bot.user_memory[chat_id]["settings"], {})
        self.assertEqual(len(katana_bot.user_memory[chat_id]["history"]), 1)
        # Make a deep copy of the specific user's data for later comparison
        original_user_data_before_save = copy.deepcopy(katana_bot.user_memory[chat_id])

        # 2. Save state
        temp_state_file = Path("test_user_state_temp.json")
        original_user_state_file_val = katana_bot.USER_STATE_FILE # Store the original Path object
        katana_bot.USER_STATE_FILE = temp_state_file

        try:
            katana_bot.save_user_state()
            self.assertTrue(temp_state_file.exists(), "State file was not created.")

            # 3. Clear in-memory state for the specific user to simulate reload
            # We need to preserve other users' states if any, so just delete the specific chat_id
            if chat_id in katana_bot.user_memory:
                 del katana_bot.user_memory[chat_id]
            self.assertNotIn(chat_id, katana_bot.user_memory)

            # If user_memory becomes empty, load_user_state might re-initialize it as {}
            # To ensure load_user_state actually loads from file, we can set user_memory to a marker
            katana_bot.user_memory = {"marker_for_test": "value"}


            # 4. Load state
            katana_bot.load_user_state() # This should reload from temp_state_file
            self.assertIn(chat_id, katana_bot.user_memory, "User state was not loaded.")
            self.assertNotIn("marker_for_test", katana_bot.user_memory, "User memory was not fully replaced by loaded data.")


            # 5. Verify loaded state matches original
            loaded_user_data = katana_bot.user_memory[chat_id]

            # Compare settings
            self.assertEqual(loaded_user_data.get("settings"), original_user_data_before_save.get("settings"), "Settings mismatch.")

            # Compare history (ensure it's a list and contents match)
            self.assertIsInstance(loaded_user_data.get("history"), list, "Loaded history is not a list.")
            self.assertEqual(len(loaded_user_data.get("history", [])), len(original_user_data_before_save.get("history", [])), "History length mismatch.")
            if original_user_data_before_save.get("history"): # Only compare if original history existed
                 self.assertEqual(loaded_user_data["history"], original_user_data_before_save["history"], "History content mismatch.")

            # Compare context (selected fields)
            self.assertIsInstance(loaded_user_data.get("context"), dict, "Loaded context is not a dict.")
            self.assertEqual(loaded_user_data.get("context", {}).get("last_recognized_intent"),
                             original_user_data_before_save.get("context", {}).get("last_recognized_intent"), "last_recognized_intent mismatch.")
            self.assertEqual(loaded_user_data.get("context", {}).get("entities"),
                             original_user_data_before_save.get("context", {}).get("entities"), "Entities mismatch.")
            self.assertEqual(loaded_user_data.get("context", {}).get("last_processed_intent"), "test_intent") # From mock_analyze

        finally:
            # Clean up: restore original USER_STATE_FILE and delete temp file
            katana_bot.USER_STATE_FILE = original_user_state_file_val
            if temp_state_file.exists():
                temp_state_file.unlink()


# --- Old tests for JSON command handling (can be adapted or removed if JSON interface is deprecated) ---
# class TestBotJSON(unittest.TestCase):
#
#     def setUp(self):
#         self.test_commands_dir = Path("test_commands_temp_dir_json")
#         self.test_commands_dir.mkdir(parents=True, exist_ok=True)
#
#         self.original_command_file_dir = katana_bot.COMMAND_FILE_DIR
#         katana_bot.COMMAND_FILE_DIR = self.test_commands_dir
#
#         self.mock_telebot_instance = MagicMock()
#         self.telebot_patcher = patch('bot.katana_bot.bot', self.mock_telebot_instance)
#         self.mock_telebot_instance_patched = self.telebot_patcher.start()
#
#         self.mock_datetime_patcher = patch('bot.katana_bot.datetime')
#         self.mock_datetime = self.mock_datetime_patcher.start()
#         self.mock_datetime.utcnow.return_value.strftime.return_value = "YYYYMMDD_HHMMSS_ffffff"
#
#     def tearDown(self):
#         self.telebot_patcher.stop()
#         self.mock_datetime_patcher.stop()
#         if self.test_commands_dir.exists():
#             shutil.rmtree(self.test_commands_dir)
#         katana_bot.COMMAND_FILE_DIR = self.original_command_file_dir
#
#     def _create_mock_json_message(self, json_payload_dict, chat_id=999):
#         mock_message = MagicMock()
#         mock_message.chat.id = chat_id
#         mock_message.text = json.dumps(json_payload_dict)
#         mock_message.content_type = 'text' # Assuming JSON comes as text
#         return mock_message
#
#     def test_valid_json_command_gets_saved(self):
#         command = {"type": "test_json_type", "module": "test_json_module", "args": {}, "id": "test_json_id"}
#         mock_message = self._create_mock_json_message(command)
#
#         # We need a way to route to handle_json_command_message.
#         # For now, let's assume it's directly called if the text is JSON.
#         # This part of the test needs adjustment based on final routing for JSON.
#         # If JSON handling is via a specific command like /json_cmd, that needs to be simulated.
#         # For now, let's call it directly for test purposes.
#         katana_bot.handle_json_command_message(mock_message)
#
#         expected_module_dir = self.test_commands_dir / "telegram_mod_test_json_module"
#         self.assertTrue(expected_module_dir.exists())
#
#         expected_filename = f"json_cmd_YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
#         expected_file_path = expected_module_dir / expected_filename
#         self.assertTrue(expected_file_path.exists())
#
#         with open(expected_file_path, "r") as f:
#             saved_data = json.load(f)
#         self.assertEqual(saved_data, command)
#
#         self.mock_telebot_instance_patched.reply_to.assert_called_once()
#         args, _ = self.mock_telebot_instance_patched.reply_to.call_args
#         self.assertEqual(args[0], mock_message)
#         self.assertTrue(args[1].startswith("✅ JSON Command received and saved as"))


if __name__ == '__main__':
    unittest.main()
