import unittest
import logging
import os
import shutil
from unittest.mock import patch, MagicMock
from katana.trader_agent import TraderAgent, TRADER_LOG_FILE, LOG_DIR

class TestTraderAgent(unittest.TestCase):

    def setUp(self):
        # Clean up before each test
        if os.path.exists(LOG_DIR):
            shutil.rmtree(LOG_DIR)
        os.makedirs(LOG_DIR)
        self.agent_btc = TraderAgent(symbol="BTC-USD")
        self.agent_eth = TraderAgent(symbol="ETH-USD")

    def tearDown(self):
        # Clean up after each test
        if os.path.exists(LOG_DIR):
            shutil.rmtree(LOG_DIR)

    def test_initialization(self):
        self.assertEqual(self.agent_btc.symbol, "BTC-USD")
        self.assertEqual(self.agent_eth.symbol, "ETH-USD")

    @patch("katana.trader_agent.TraderAgent.get_current_price", return_value=50000.0)
    @patch("katana.trader_agent.trader_logger")
    def test_make_decision_logging_calls(self, mock_trader_logger, mock_get_price):
        # Create a mock for the logger's info method
        mock_info = MagicMock()
        mock_trader_logger.info = mock_info

        self.agent_btc.make_decision()

        # Check that the logger was called
        self.assertTrue(mock_info.called)

        # Consolidate all log messages into a single string for easier checking
        logged_messages = " ".join(str(call) for call in mock_info.call_args_list)

        self.assertIn(f"Analyzing market for {self.agent_btc.symbol}", logged_messages)
        self.assertIn("LEARNING_MODE_DECISION", logged_messages)

if __name__ == "__main__":
    unittest.main()
