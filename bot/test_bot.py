import unittest
from unittest.mock import MagicMock, patch
import copy
import os

from bot import katana_bot
from bot.nlp import context as nlp_context

class TestKatanaBotWithOpenAI(unittest.TestCase):

    def setUp(self):
        # Mock the Telebot instance
        self.mock_telebot_instance = MagicMock()
        self.telebot_patcher = patch('bot.katana_bot.bot', self.mock_telebot_instance)
        self.mock_telebot_instance_patched = self.telebot_patcher.start()

        # Clear user memory for each test
        self.original_user_memory = copy.deepcopy(katana_bot.user_memory)
        katana_bot.user_memory.clear()

        # Mock datetime
        self.mock_datetime_patcher = patch('bot.katana_bot.datetime')
        self.mock_datetime = self.mock_datetime_patcher.start()
        self.mock_datetime.utcnow.return_value.isoformat.return_value = "TEST_TIMESTAMP"
        self.mock_datetime.now.return_value.strftime.return_value = "TEST_TIME"

        # Set a dummy API token to prevent ValueError during module import
        self.env_patcher = patch.dict(os.environ, {"KATANA_TELEGRAM_TOKEN": "123456:ABC-DEF", "OPENAI_API_KEY": "dummy-key"})
        self.env_patcher.start()

    def tearDown(self):
        self.telebot_patcher.stop()
        self.mock_datetime_patcher.stop()
        self.env_patcher.stop()
        katana_bot.user_memory = self.original_user_memory

    def _create_mock_message(self, text, chat_id=12345):
        mock_message = MagicMock()
        mock_message.chat.id = chat_id
        mock_message.text = text
        mock_message.content_type = 'text'
        return mock_message

    @patch('bot.nlp.parser.get_nlp_processor')
    def test_search_documents_intent(self, mock_get_nlp_processor):
        # 1. Setup the mock NLP response
        mock_processor = mock_get_nlp_processor.return_value
        mock_openai_response = {
            "intent": "search_documents",
            "entities": [
                {"text": "Sapiens Coin", "type": "document_name"},
                {"text": "прошлая неделя", "type": "time_range"}
            ],
            "keywords": ["Sapiens Coin", "данные", "прошлая неделя"],
            "sentiment": "neutral",
            "dialogue_state": "new_request"
        }
        mock_processor.process_text.return_value = mock_openai_response

        # 2. Create a mock message and call the handler
        mock_message = self._create_mock_message("Найди мне данные по Sapiens Coin за прошлую неделю")

        # We need a handler for 'search_documents' for the test to pass
        # Let's add a dummy one for now.
        def handle_search_documents(chat_id, entities, context):
            doc = entities.get("document_name", "неизвестный документ")
            time = entities.get("time_range", "неизвестное время")
            return f"Начинаю поиск документа '{doc}' за '{time}'."

        original_handler = katana_bot.INTENT_HANDLERS.get("search_documents")
        katana_bot.INTENT_HANDLERS["search_documents"] = handle_search_documents

        katana_bot.handle_user_chat_message(mock_message)

        # 3. Assertions
        # Check that the NLP processor was called correctly
        mock_processor.process_text.assert_called_once_with("Найди мне данные по Sapiens Coin за прошлую неделю", dialogue_history=[])

        # Check that the bot replied with the correct text from our dummy handler
        self.mock_telebot_instance_patched.reply_to.assert_called_once()
        args, _ = self.mock_telebot_instance_patched.reply_to.call_args
        self.assertEqual(args[0], mock_message)
        self.assertIn("Начинаю поиск документа 'Sapiens Coin' за 'прошлая неделя'", args[1])

        # Restore original handler
        if original_handler:
            katana_bot.INTENT_HANDLERS["search_documents"] = original_handler
        else:
            del katana_bot.INTENT_HANDLERS["search_documents"]

    @patch('bot.nlp.parser.get_nlp_processor')
    def test_get_weather_intent_with_mocked_openai(self, mock_get_nlp_processor):
        # 1. Setup mock NLP response
        mock_processor = mock_get_nlp_processor.return_value
        mock_openai_response = {
            "intent": "get_weather",
            "entities": [{"text": "Москве", "type": "location"}],
            "keywords": ["погода", "Москва"],
            "sentiment": "neutral",
            "dialogue_state": "new_request"
        }
        mock_processor.process_text.return_value = mock_openai_response

        # 2. Call handler
        mock_message = self._create_mock_message("какая погода в Москве", chat_id=200)
        katana_bot.handle_user_chat_message(mock_message)

        # 3. Assertions
        self.mock_telebot_instance_patched.reply_to.assert_called_once()
        args, _ = self.mock_telebot_instance_patched.reply_to.call_args
        self.assertEqual(args[0], mock_message)
        self.assertIn("Погода в городе Москве отличная!", args[1])

        # Check that the bot's context was updated correctly
        chat_id = 200
        self.assertIn(chat_id, katana_bot.user_memory)
        # The adapter logic in parser.py converts 'location' to 'city'
        self.assertEqual(katana_bot.user_memory[chat_id]["context"]["entities"].get("city"), "Москве")
        self.assertEqual(katana_bot.user_memory[chat_id]["context"]["last_processed_intent"], "get_weather")

    @patch('bot.nlp.parser.get_nlp_processor')
    def test_fallback_intent_from_openai(self, mock_get_nlp_processor):
        # 1. Setup mock NLP response for an unclear intent
        mock_processor = mock_get_nlp_processor.return_value
        mock_openai_response = {
            "intent": "fallback_general",
            "entities": [],
            "keywords": ["абракадабра"],
            "sentiment": "neutral",
            "dialogue_state": "new_request"
        }
        mock_processor.process_text.return_value = mock_openai_response

        # 2. Call handler
        mock_message = self._create_mock_message("абракадабра", chat_id=500)
        katana_bot.handle_user_chat_message(mock_message)

        # 3. Assertions
        self.mock_telebot_instance_patched.reply_to.assert_called_once()
        args, _ = self.mock_telebot_instance_patched.reply_to.call_args
        self.assertIn(args[1], [
            "Я не совсем понял, что вы имеете в виду. Можете переформулировать?",
            "Хм, я пока не умею на это отвечать. Попробуйте что-нибудь другое.",
            "Извините, я не распознал вашу команду. Может, попробуем что-то из этого: погода, факт, анекдот?"
        ])
        self.assertEqual(katana_bot.user_memory[500]["context"]["last_processed_intent"], "fallback_general")

    @patch('bot.nlp.parser.get_nlp_processor')
    def test_dialogue_continuation(self, mock_get_nlp_processor):
        chat_id = 900
        mock_processor = mock_get_nlp_processor.return_value

        # --- Turn 1: Initial Search ---
        mock_openai_response_1 = {
            "intent": "search_documents",
            "entities": [{"text": "Sapiens Coin", "type": "document_name"}],
            "dialogue_state": "new_request"
        }
        mock_processor.process_text.return_value = mock_openai_response_1

        # Add a dummy handler for search_documents
        katana_bot.INTENT_HANDLERS["search_documents"] = lambda c, e, ctx: f"Found document: {e.get('document_name')}"

        mock_message_1 = self._create_mock_message("Найди отчет по Sapiens Coin", chat_id=chat_id)
        katana_bot.handle_user_chat_message(mock_message_1)

        # Assertions for Turn 1
        self.assertEqual(katana_bot.user_memory[chat_id]["context"]["entities"].get("document_name"), "Sapiens Coin")
        mock_processor.process_text.assert_called_once_with("Найди отчет по Sapiens Coin", dialogue_history=[])

        # --- Turn 2: Continuation ---
        mock_openai_response_2 = {
            "intent": "sort_results",
            "entities": [{"text": "по дате", "type": "sort_by"}],
            "dialogue_state": "continuation"
        }
        mock_processor.process_text.return_value = mock_openai_response_2

        # Add a dummy handler for the new intent
        katana_bot.INTENT_HANDLERS["sort_results"] = lambda c, e, ctx: f"Sorting {e.get('document_name')} by {e.get('sort_by')}"

        mock_message_2 = self._create_mock_message("отсортируй по дате", chat_id=chat_id)
        katana_bot.handle_user_chat_message(mock_message_2)

        # Assertions for Turn 2
        # Check that history was passed to the NLP processor
        self.assertEqual(mock_processor.process_text.call_count, 2)
        args, kwargs = mock_processor.process_text.call_args
        self.assertEqual(args[0], "отсортируй по дате")
        self.assertIn({'role': 'user', 'content': 'Найди отчет по Sapiens Coin'}, kwargs['dialogue_history'])

        # Check that the bot's final reply uses context from the first turn
        self.mock_telebot_instance_patched.reply_to.assert_called_with(
            mock_message_2,
            "Sorting Sapiens Coin by по дате"
        )

        # Check that the context still holds the original document name
        self.assertEqual(katana_bot.user_memory[chat_id]["context"]["entities"].get("document_name"), "Sapiens Coin")

        # Cleanup dummy handlers
        del katana_bot.INTENT_HANDLERS["search_documents"]
        del katana_bot.INTENT_HANDLERS["sort_results"]


if __name__ == '__main__':
    # We need to add this to run tests directly from the file
    import os
    # Set dummy env vars for direct execution
    os.environ["KATANA_TELEGRAM_TOKEN"] = "123456:ABC-DEF"
    os.environ["OPENAI_API_KEY"] = "dummy-key-for-testing"
    unittest.main()
