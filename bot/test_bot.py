import unittest
from unittest.mock import patch
import os

from bot.katana_bot import KatanaBot

class TestKatanaBotRefactored(unittest.TestCase):

    def setUp(self):
        """Set up the test environment for each test."""
        self.env_patcher = patch.dict(os.environ, {"OPENAI_API_KEY": "dummy-key-for-testing"})
        self.env_patcher.start()

        # Patch the Parser's analyze_text method directly, as this is the
        # bot's direct interface with the NLP subsystem.
        self.parser_patcher = patch('bot.katana_bot.Parser.analyze_text')
        self.mock_analyze_text = self.parser_patcher.start()

        # Instantiate our bot for API usage (no telebot)
        self.bot = KatanaBot(use_telebot=False)

    def tearDown(self):
        """Clean up after each test."""
        self.env_patcher.stop()
        self.parser_patcher.stop()

    def _prepare_parser_mock_response(self, intent, entities=None, state="new_request"):
        """Helper to create a mock response from the Parser."""
        if entities is None:
            entities = {}
        return {
            "intents": [{"name": intent}],
            "entities": entities,
            "metadata": {"raw_openai_response": {"dialogue_state": state}}
        }

    def test_initial_search_and_continuation(self):
        """
        Tests a two-turn conversation to ensure context is maintained.
        """
        chat_id = 999

        # --- Turn 1: Initial search query ---
        mock_response_1 = self._prepare_parser_mock_response(
            "search_documents",
            entities={"document_name": "Q3 Financials"}
        )
        self.mock_analyze_text.return_value = mock_response_1
        self.bot.intent_handlers['search_documents'] = lambda cid, e, ctx: f"Found doc: {e.get('document_name')}"

        result1 = self.bot.process_chat_message(chat_id, "find the Q3 Financials report")

        # Assertions for Turn 1
        self.mock_analyze_text.assert_called_once_with("find the Q3 Financials report", history=[])
        self.assertEqual(result1['reply'], "Found doc: Q3 Financials")
        self.assertIn("document_name", self.bot.sessions[chat_id]["context"]["entities"])

        # --- Turn 2: Follow-up command ---
        self.mock_analyze_text.reset_mock()
        mock_response_2 = self._prepare_parser_mock_response(
            "sort_results",
            entities={"sort_by": "by date"},
            state="continuation"
        )
        self.mock_analyze_text.return_value = mock_response_2
        self.bot.intent_handlers['sort_results'] = lambda cid, e, ctx: f"Sorting {e.get('document_name')} {e.get('sort_by')}"

        result2 = self.bot.process_chat_message(chat_id, "now sort it by date")

        # Assertions for Turn 2
        history_arg = self.mock_analyze_text.call_args.kwargs['history']
        self.assertIn("find the Q3 Financials report", history_arg[0]['user'])
        self.assertEqual(result2['reply'], "Sorting Q3 Financials by date")
        self.assertEqual(self.bot.sessions[chat_id]["context"]["entities"]["document_name"], "Q3 Financials")
        self.assertEqual(self.bot.sessions[chat_id]["context"]["entities"]["sort_by"], "by date")

    def test_new_request_clears_context(self):
        """
        Tests that a new request clears the entities from the previous context.
        """
        chat_id = 888

        # --- Turn 1: Populate context ---
        mock_response_1 = self._prepare_parser_mock_response("search_documents", {"document_name": "Old Doc"})
        self.mock_analyze_text.return_value = mock_response_1
        self.bot.intent_handlers['search_documents'] = lambda cid, e, ctx: "..."

        self.bot.process_chat_message(chat_id, "find Old Doc")
        self.assertEqual(self.bot.sessions[chat_id]["context"]["entities"]["document_name"], "Old Doc")

        # --- Turn 2: A new request ---
        self.mock_analyze_text.reset_mock()
        mock_response_2 = self._prepare_parser_mock_response("tell_joke")
        self.mock_analyze_text.return_value = mock_response_2

        self.bot.process_chat_message(chat_id, "tell me a joke")

        # Assert that the old entity has been cleared
        self.assertNotIn("document_name", self.bot.sessions[chat_id]["context"]["entities"])

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
