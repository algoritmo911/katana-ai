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
            "Извините, я не распознал вашу команду. Может, попробуем что-то из этого: погода, факт, анекдот?"
        ])
        # This test is for a generic fallback, so it should be fallback_general
        self.assertEqual(katana_bot.user_memory[chat_id]["context"]["last_processed_intent"], "fallback_general")

    def test_fallback_clarification_needed(self):
        chat_id = 501
        # Сообщение, которое может извлечь сущность, но неясный интент
        mock_message = self._create_mock_message("расскажи про Лондон", chat_id=chat_id)

        # Ожидаем, что nlp_parser извлечет "Лондон", но не найдет четкого интента "расскажи про"
        # и вернет fallback_clarification_needed

        # Чтобы это проверить более изолированно, можно было бы мокнуть nlp_parser.analyze_text,
        # но пока протестируем через полный handle_user_chat_message

        katana_bot.handle_user_chat_message(mock_message)

        self.mock_telebot_instance_patched.reply_to.assert_called_once()
        args, _ = self.mock_telebot_instance_patched.reply_to.call_args

        # Проверяем, что ответ содержит упоминание извлеченной сущности
        self.assertIn("Лондон", args[1])
        self.assertIn("уточнить", args[1].lower())

        self.assertEqual(katana_bot.user_memory[chat_id]["context"]["last_processed_intent"], "fallback_clarification_needed")
        self.assertIsNotNone(katana_bot.user_memory[chat_id]["history"][0]["nlp_result"]["fallback_type"])
        self.assertEqual(katana_bot.user_memory[chat_id]["history"][0]["nlp_result"]["fallback_type"], "clarification_needed")


    def test_weather_frame_activation_and_population(self):
        chat_id = 502
        # 1. Спрашиваем погоду с городом
        mock_message1 = self._create_mock_message("какая погода в Лондоне", chat_id=chat_id)
        katana_bot.handle_user_chat_message(mock_message1)

        self.mock_telebot_instance_patched.reply_to.assert_called_with(mock_message1, "☀️ Погода в городе Лондоне отличная! (но это не точно)")
        history_entry1 = katana_bot.user_memory[chat_id]["history"][0]
        nlp_result1 = history_entry1["nlp_result"]

        self.assertIn("active_frames", nlp_result1)
        self.assertEqual(len(nlp_result1["active_frames"]), 1)
        weather_frame1 = nlp_result1["active_frames"][0]
        self.assertEqual(weather_frame1["name"], "weather_inquiry_frame")
        self.assertEqual(weather_frame1["slots"]["city"], "Лондоне")
        self.assertEqual(weather_frame1["status"], "ready_to_fulfill") # Город есть

        # 2. Спрашиваем погоду без города (контекст пуст)
        katana_bot.user_memory.clear() # Очищаем память для чистоты теста этого шага
        mock_message2 = self._create_mock_message("а погода?", chat_id=chat_id)
        katana_bot.handle_user_chat_message(mock_message2)

        self.mock_telebot_instance_patched.reply_to.assert_called_with(mock_message2, "Для какого города вы хотите узнать погоду?")
        history_entry2 = katana_bot.user_memory[chat_id]["history"][0]
        nlp_result2 = history_entry2["nlp_result"]

        self.assertIn("active_frames", nlp_result2)
        self.assertEqual(len(nlp_result2["active_frames"]), 1)
        weather_frame2 = nlp_result2["active_frames"][0]
        self.assertEqual(weather_frame2["name"], "weather_inquiry_frame")
        self.assertIsNone(weather_frame2["slots"]["city"]) # Города нет
        self.assertEqual(weather_frame2["status"], "incomplete")
        # Также проверяем, что интент изменился на уточняющий
        self.assertEqual(nlp_result2["intents"][0]["name"], "clarify_city_for_weather")

        # 3. Пользователь отвечает городом
        mock_message3 = self._create_mock_message("Питер", chat_id=chat_id)
        katana_bot.handle_user_chat_message(mock_message3)

        self.mock_telebot_instance_patched.reply_to.assert_called_with(mock_message3, "☀️ Погода в городе Питер отличная! (но это не точно)")
        history_entry3 = katana_bot.user_memory[chat_id]["history"][1] # Вторая запись в истории этого чата
        nlp_result3 = history_entry3["nlp_result"]

        self.assertIn("active_frames", nlp_result3)
        self.assertEqual(len(nlp_result3["active_frames"]), 1)
        weather_frame3 = nlp_result3["active_frames"][0]
        self.assertEqual(weather_frame3["name"], "weather_inquiry_frame")
        self.assertEqual(weather_frame3["slots"]["city"], "Питер")
        self.assertEqual(weather_frame3["status"], "completed_after_clarification")


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

    def test_response_generation_frame_incomplete(self):
        chat_id = 701
        # Mock nlp_result for this specific test
        mock_nlp_result = {
            "text": "погода",
            "intents": [{"name": "clarify_city_for_weather", "confidence": 0.95}], # This would be set by parser
            "entities": {},
            "active_frames": [{
                "name": "weather_inquiry_frame",
                "slots": {"city": None, "date": "today"},
                "status": "incomplete"
            }],
            "fallback_type": None
        }
        with patch('bot.katana_bot.nlp_parser.analyze_text', return_value=mock_nlp_result):
            mock_message = self._create_mock_message("погода", chat_id=chat_id)
            katana_bot.handle_user_chat_message(mock_message)

        self.mock_telebot_instance_patched.reply_to.assert_called_with(
            mock_message,
            "Для какого города вы хотите узнать погоду?"
        )
        # Check that clarify_city_for_weather was processed
        processed_info = katana_bot.user_memory[chat_id]["history"][0]["processed_intents"]
        self.assertTrue(any(p["name"] == "clarify_city_for_weather" and p["processed"] for p in processed_info))

    def test_response_generation_frame_complete_and_other_intent(self):
        chat_id = 702
        mock_nlp_result = {
            "text": "погода в Лондоне и расскажи анекдот",
            "intents": [ # Parser might order them by internal logic or confidence
                {"name": "get_weather", "confidence": 0.9},
                {"name": "tell_joke", "confidence": 0.85}
            ],
            "entities": {"city": "Лондоне"},
            "active_frames": [{
                "name": "weather_inquiry_frame",
                "slots": {"city": "Лондоне", "date": "today"},
                "status": "ready_to_fulfill"
            }],
            "fallback_type": None
        }

        # Mock random.choice for tell_joke to get a predictable joke
        with patch('bot.katana_bot.nlp_parser.analyze_text', return_value=mock_nlp_result), \
             patch('random.choice', side_effect=lambda x: x[0] if x[0] == "Колобок повесился." else random.SystemRandom().choice(x)): # Ensure joke is predictable

            mock_message = self._create_mock_message("погода в Лондоне и расскажи анекдот", chat_id=chat_id)
            katana_bot.handle_user_chat_message(mock_message)

        args, _ = self.mock_telebot_instance_patched.reply_to.call_args
        response_text = args[1]

        # Frame-related intent (get_weather) should be prioritized.
        # Then other intents (tell_joke). Greeting is not present here.
        expected_weather_response = "☀️ Погода в городе Лондоне отличная! (но это не точно)"
        expected_joke_response = "Колобок повесился." # First joke from the list

        self.assertIn(expected_weather_response, response_text)
        self.assertIn(expected_joke_response, response_text)
        # Check order: weather response should appear before joke response due to frame logic
        self.assertTrue(response_text.find(expected_weather_response) < response_text.find(expected_joke_response))

        processed_info = katana_bot.user_memory[chat_id]["history"][0]["processed_intents"]
        self.assertTrue(any(p["name"] == "get_weather" and p["processed"] for p in processed_info))
        self.assertTrue(any(p["name"] == "tell_joke" and p["processed"] for p in processed_info))


    def test_response_generation_greeting_and_frame_intent(self):
        chat_id = 703
        mock_nlp_result = {
            "text": "Привет, какая погода в Москве",
            "intents": [
                {"name": "greeting", "confidence": 0.95},
                {"name": "get_weather", "confidence": 0.9},
            ],
            "entities": {"city": "Москве"},
            "active_frames": [{
                "name": "weather_inquiry_frame",
                "slots": {"city": "Москве", "date": "today"},
                "status": "ready_to_fulfill" # or completed_after_clarification
            }],
            "fallback_type": None
        }

        # Mock random.choice for greeting to get a predictable greeting
        with patch('bot.katana_bot.nlp_parser.analyze_text', return_value=mock_nlp_result), \
             patch('random.choice', side_effect=lambda x: x[0] if x[0] == "Привет!" else random.SystemRandom().choice(x)):

            mock_message = self._create_mock_message("Привет, какая погода в Москве", chat_id=chat_id)
            katana_bot.handle_user_chat_message(mock_message)

        args, _ = self.mock_telebot_instance_patched.reply_to.call_args
        response_text = args[1]

        expected_greeting = "Привет!"
        expected_weather = "☀️ Погода в городе Москве отличная! (но это не точно)"

        # Order: Greeting first, then frame-driven weather response.
        self.assertTrue(response_text.startswith(expected_greeting), f"Response '{response_text}' did not start with '{expected_greeting}'")
        self.assertIn(expected_weather, response_text)

        processed_info = katana_bot.user_memory[chat_id]["history"][0]["processed_intents"]
        greeting_processed = next(p for p in processed_info if p["name"] == "greeting")
        weather_processed = next(p for p in processed_info if p["name"] == "get_weather")

        self.assertTrue(greeting_processed["processed"])
        self.assertTrue(weather_processed["processed"])
        # Check that greeting was marked as part of multi-response if weather also triggered
        self.assertTrue(greeting_processed.get("is_greeting_multi", False))

    def test_metrics_logging_contextual_linkage_entity_used(self):
        chat_id = 801
        # Setup initial context with an entity
        katana_bot.user_memory[chat_id] = {
            "context": {"entities": {"city": "Лондон"}, "last_processed_intent": "some_previous_intent"},
            "history": []
        }

        # Mock NLP result that uses this city
        mock_nlp_result = {
            "text": "какая там погода",
            "intents": [{"name": "get_weather", "confidence": 0.9}],
            "entities": {"city": "Лондон"}, # NLP confirms/re-extracts city
            "active_frames": [{"name": "weather_inquiry_frame", "slots": {"city": "Лондон"}, "status": "ready_to_fulfill"}],
            "fallback_type": None
        }

        with patch('bot.katana_bot.nlp_parser.analyze_text', return_value=mock_nlp_result), \
             patch('bot.katana_bot.log_local_bot_event') as mock_log_event:
            mock_message = self._create_mock_message("какая там погода", chat_id=chat_id)
            katana_bot.handle_user_chat_message(mock_message)

        # Find the KATANA_METRICS log call
        metrics_log_call = None
        for call_args in mock_log_event.call_args_list:
            if "KATANA_METRICS:" in call_args[0][0]:
                metrics_log_call = call_args[0][0]
                break

        self.assertIsNotNone(metrics_log_call, "KATANA_METRICS log not found.")
        metrics_json_str = metrics_log_call.split("KATANA_METRICS: ")[1]
        metrics_data = json.loads(metrics_json_str)

        self.assertEqual(metrics_data["contextual_linkage_score"], 1) # City "Лондон" was used
        self.assertEqual(metrics_data["primary_intent_name"], "get_weather")

    def test_metrics_logging_frame_continuation_linkage(self):
        chat_id = 802
        # 1. First message: Ask for weather, intent becomes clarify_city_for_weather
        mock_message1 = self._create_mock_message("какая погода", chat_id=chat_id)
        with patch('bot.katana_bot.log_local_bot_event') as mock_log_event_step1: # Suppress logs for this part
            katana_bot.handle_user_chat_message(mock_message1)

        # 2. Second message: Provide city, completing the frame
        mock_nlp_result_step2 = {
            "text": "в Москве",
            "intents": [{"name": "get_weather", "confidence": 0.85}],
            "entities": {"city": "Москве"},
            "active_frames": [{"name": "weather_inquiry_frame", "slots": {"city": "Москве"}, "status": "completed_after_clarification"}],
            "fallback_type": None
        }
        with patch('bot.katana_bot.nlp_parser.analyze_text', return_value=mock_nlp_result_step2), \
             patch('bot.katana_bot.log_local_bot_event') as mock_log_event_step2:
            mock_message2 = self._create_mock_message("в Москве", chat_id=chat_id)
            katana_bot.handle_user_chat_message(mock_message2)

        metrics_log_call = None
        for call_args in mock_log_event_step2.call_args_list:
            if "KATANA_METRICS:" in call_args[0][0]:
                metrics_log_call = call_args[0][0]
                break

        self.assertIsNotNone(metrics_log_call, "KATANA_METRICS log not found for step 2.")
        metrics_json_str = metrics_log_call.split("KATANA_METRICS: ")[1]
        metrics_data = json.loads(metrics_json_str)

        # Expecting linkage score to be at least 1 due to frame continuation.
        # If "city" was also in prev_context.entities and matched, it could be 2.
        # Here, prev_context.entities would be empty from clarify_city_for_weather.
        self.assertGreaterEqual(metrics_data["contextual_linkage_score"], 1)
        self.assertEqual(metrics_data["primary_intent_name"], "get_weather")
        self.assertEqual(metrics_data["active_frames_count"], 1)

    def test_metrics_logging_fallback_details(self):
        chat_id = 803
        mock_nlp_result = {
            "text": "fsdhjfgsdjhfg",
            "intents": [{"name": "fallback_general", "confidence": 1.0}],
            "entities": {},
            "active_frames": [],
            "fallback_type": "general" # Explicitly set by parser
        }
        with patch('bot.katana_bot.nlp_parser.analyze_text', return_value=mock_nlp_result), \
             patch('bot.katana_bot.log_local_bot_event') as mock_log_event:
            mock_message = self._create_mock_message("fsdhjfgsdjhfg", chat_id=chat_id)
            katana_bot.handle_user_chat_message(mock_message)

        metrics_log_call = None
        for call_args in mock_log_event.call_args_list:
            if "KATANA_METRICS:" in call_args[0][0]:
                metrics_log_call = call_args[0][0]
                break

        self.assertIsNotNone(metrics_log_call, "KATANA_METRICS log not found.")
        metrics_json_str = metrics_log_call.split("KATANA_METRICS: ")[1]
        metrics_data = json.loads(metrics_json_str)

        self.assertEqual(metrics_data["primary_intent_name"], "fallback_general")
        self.assertEqual(metrics_data["primary_intent_confidence"], "1.00")
        self.assertEqual(metrics_data["used_fallback_type"], "general")
        # This should be False because fallback_general is a handled intent from the parser
        self.assertFalse(metrics_data["is_final_fallback_handler_used"])


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
