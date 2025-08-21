import unittest
from unittest.mock import patch, MagicMock

from katana.oracle import Oracle

class TestOracle(unittest.TestCase):

    @patch('katana.oracle.SummarizerAgent')
    @patch('katana.oracle.WebSearchAgent')
    @patch('katana.oracle.PriceAgent')
    def test_query_orchestration_success(self, MockPriceAgent, MockWebSearchAgent, MockSummarizerAgent):
        """
        Tests that the Oracle correctly orchestrates the specialist agents for a valid query.
        """
        # --- Arrange ---
        # Mock the instances that will be created inside the query method
        mock_price_agent = MockPriceAgent.return_value
        mock_web_search_agent = MockWebSearchAgent.return_value
        mock_summarizer_agent = MockSummarizerAgent.return_value

        # Set up the return values for the 'execute' calls
        mock_price_agent.execute.return_value = {"price": "50000", "currency": "USD"}
        mock_web_search_agent.execute.return_value = {"results": ["Some news."]}
        mock_summarizer_agent.execute.return_value = "This is the final synthesized answer."

        # Instantiate the Oracle
        oracle = Oracle()

        question = "What is the price of BTC-USD and what is the latest news?"

        # --- Act ---
        result = oracle.query(question)

        # --- Assert ---
        # 1. Verify that PriceAgent was called correctly
        MockPriceAgent.assert_called_once()
        mock_price_agent.execute.assert_called_once_with({
            "action": "get_spot_price",
            "product_id": "BTC-USD"
        })

        # 2. Verify that WebSearchAgent was called correctly
        MockWebSearchAgent.assert_called_once()
        mock_web_search_agent.execute.assert_called_once_with({
            "action": "web_search",
            "query": "BTC-USD crypto news"
        })

        # 3. Verify that SummarizerAgent was called correctly
        MockSummarizerAgent.assert_called_once()
        # Check the 'text' argument passed to the summarizer
        summarizer_call_args = mock_summarizer_agent.execute.call_args[0][0]
        self.assertIn("Price Information: The price of BTC-USD is 50000 USD.", summarizer_call_args['text'])
        self.assertIn("News Information: Web search results: ['Some news.']", summarizer_call_args['text'])
        self.assertEqual(summarizer_call_args['user_prompt'], question)

        # 4. Verify the final result
        self.assertEqual(result, "This is the final synthesized answer.")

    def test_query_invalid_question(self):
        """
        Tests that the Oracle returns a default message for a question it cannot handle.
        """
        # --- Arrange ---
        oracle = Oracle()
        question = "How are you today?"

        # --- Act ---
        result = oracle.query(question)

        # --- Assert ---
        expected_response = "I can currently only answer questions about the price and news of a specific asset, like 'What is the price of BTC-USD and what is the latest news?'"
        self.assertEqual(result, expected_response)

if __name__ == "__main__":
    unittest.main()
