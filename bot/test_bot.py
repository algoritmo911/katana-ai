import unittest
from unittest.mock import MagicMock, patch, ANY
import os
import json

# Import the new classes
from bot.katana_bot import KatanaBot
from bot.nlp.nlp_processor import NLPProcessor
from bot.nlp.parser import Parser
from bot.nlp.context import DialogueContextManager

class TestKatanaBotRefactored(unittest.TestCase):

    def setUp(self):
        """Set up the test environment for each test."""
        # Set dummy environment variables required by the bot
        self.env_patcher = patch.dict(os.environ, {
            "KATANA_TELEGRAM_TOKEN": "123456:ABC-DEF",
            "OPENAI_API_KEY": "dummy-key-for-testing"
        })
        self.env_patcher.start()

        # We patch the TeleBot instance at the class level to prevent real API calls
        self.telebot_patcher = patch('telebot.TeleBot')
        self.mock_telebot_class = self.telebot_patcher.start()

        # We also patch the NLPProcessor to control its output in tests
        self.nlp_processor_patcher = patch('bot.katana_bot.NLPProcessor')
        self.mock_nlp_processor_class = self.nlp_processor_patcher.start()

        # Instantiate our bot. It will be created with mocked TeleBot and NLPProcessor
        self.bot = KatanaBot()

        # Get a direct handle to the mocked processor instance for configuring return values
        self.mock_processor_instance = self.bot.nlp_processor

    def tearDown(self):
        """Clean up after each test."""
        self.env_patcher.stop()
        self.telebot_patcher.stop()
        self.nlp_processor_patcher.stop()

    def _create_mock_message(self, text, chat_id=12345):
        """Helper to create a mock Telebot message."""
        mock_message = MagicMock()
        mock_message.chat.id = chat_id
        mock_message.text = text
        mock_message.content_type = 'text'
        return mock_message

    def test_initial_search_and_continuation(self):
        """
        Tests a two-turn conversation to ensure context is maintained.
        1. User asks to find a document.
        2. User asks to sort the results of that document.
        """
        chat_id = 999

        # --- Turn 1: Initial search query ---

        # Configure the mock NLP Processor for the first turn
        mock_response_1 = {
            "intent": "search_documents",
            "entities": [{"text": "Q3 Financials", "type": "document_name"}],
            "dialogue_state": "new_request"
        }
        self.mock_processor_instance.process_text.return_value = mock_response_1

        # Add a dummy handler for the search intent
        self.bot.intent_handlers['search_documents'] = lambda cid, e, ctx: f"Found doc: {e.get('document_name')}"

        message1 = self._create_mock_message("find the Q3 Financials report", chat_id=chat_id)
        self.bot.process_chat_message(message1)

        # Assertions for Turn 1
        self.mock_processor_instance.process_text.assert_called_once_with(
            "find the Q3 Financials report",
            dialogue_history_json='[]'  # History is empty on the first turn
        )
        self.bot.telebot.reply_to.assert_called_with(message1, "Found doc: Q3 Financials")

        # Check that the session context was updated correctly
        self.assertIn("Q3 Financials", self.bot.sessions[chat_id]["context"]["entities"]["document_name"])


        # --- Turn 2: Follow-up command (continuation) ---

        # Reset the mock for the second call
        self.mock_processor_instance.process_text.reset_mock()

        # Configure the mock NLP Processor for the second turn
        mock_response_2 = {
            "intent": "sort_results",
            "entities": [{"text": "by date", "type": "sort_by"}],
            "dialogue_state": "continuation"
        }
        self.mock_processor_instance.process_text.return_value = mock_response_2

        # Add a dummy handler for the sort intent
        self.bot.intent_handlers['sort_results'] = lambda cid, e, ctx: f"Sorting {e.get('document_name')} {e.get('sort_by')}"

        message2 = self._create_mock_message("now sort it by date", chat_id=chat_id)
        self.bot.process_chat_message(message2)

        # Assertions for Turn 2
        # Check that the call to the NLP processor included the history
        history_arg = self.mock_processor_instance.process_text.call_args.kwargs['dialogue_history_json']
        self.assertIn("find the Q3 Financials report", history_arg)

        # Check that the bot's response correctly used the merged context
        self.bot.telebot.reply_to.assert_called_with(message2, "Sorting Q3 Financials by date")

        # Check that the context still contains the entity from the first turn
        self.assertEqual(self.bot.sessions[chat_id]["context"]["entities"]["document_name"], "Q3 Financials")
        self.assertEqual(self.bot.sessions[chat_id]["context"]["entities"]["sort_by"], "by date")

    def test_new_request_clears_context(self):
        """
        Tests that a new request clears the entities from the previous context.
        """
        chat_id = 888

        # --- Turn 1: A request that populates context ---
        mock_response_1 = {"intent": "search_documents", "entities": [{"text": "Old Doc", "type": "document_name"}], "dialogue_state": "new_request"}
        self.mock_processor_instance.process_text.return_value = mock_response_1
        self.bot.intent_handlers['search_documents'] = lambda cid, e, ctx: "..."

        message1 = self._create_mock_message("find Old Doc", chat_id=chat_id)
        self.bot.process_chat_message(message1)
        self.assertEqual(self.bot.sessions[chat_id]["context"]["entities"]["document_name"], "Old Doc")

        # --- Turn 2: A completely new request ---
        self.mock_processor_instance.process_text.reset_mock()
        mock_response_2 = {"intent": "tell_joke", "entities": [], "dialogue_state": "new_request"}
        self.mock_processor_instance.process_text.return_value = mock_response_2

        message2 = self._create_mock_message("tell me a joke", chat_id=chat_id)
        self.bot.process_chat_message(message2)

        # Assert that the old 'document_name' entity has been cleared
        self.assertNotIn("document_name", self.bot.sessions[chat_id]["context"]["entities"])

if __name__ == '__main__':
    unittest.main()
