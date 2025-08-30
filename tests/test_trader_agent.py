import unittest
import logging
import os
import json
import requests
from unittest.mock import patch, MagicMock

from katana.trader_agent import (
    TraderAgent,
    TRADER_LOG_FILE,
    TRADER_DATA_LOG_FILE,
    TRADER_DATA_JSON_FILE,
    DECISIONS_JSON_FILE,
    LOG_DIR,
)


class TestTraderAgent(unittest.TestCase):

    def setUp(self):
        """
        Set up for each test. This method ensures a clean state by:
        1. Creating the log directory.
        2. Deleting any log/data files from previous runs.
        3. Re-configuring the module-level loggers to point to new file handlers,
           which solves issues with tests deleting files that loggers still have open.
        """
        os.makedirs(LOG_DIR, exist_ok=True)

        files_to_clean = [
            TRADER_LOG_FILE,
            TRADER_DATA_LOG_FILE,
            TRADER_DATA_JSON_FILE,
            DECISIONS_JSON_FILE,
        ]
        for f in files_to_clean:
            if os.path.exists(f):
                os.remove(f)

        # Re-configure loggers for each test to handle file deletion
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        trader_logger = logging.getLogger("KatanaTrader")
        trader_logger.handlers.clear()
        fh = logging.FileHandler(TRADER_LOG_FILE)
        fh.setFormatter(formatter)
        trader_logger.addHandler(fh)

        trader_data_logger = logging.getLogger("KatanaTraderData")
        trader_data_logger.handlers.clear()
        dfh = logging.FileHandler(TRADER_DATA_LOG_FILE)
        dfh.setFormatter(formatter)
        trader_data_logger.addHandler(dfh)

        self.agent_btc = TraderAgent(symbol="BTC-USD")

    def tearDown(self):
        """Clean up created files after each test."""
        # setUp handles cleaning, so this can be pass
        pass

    def test_initialization(self):
        """Test that the TraderAgent initializes correctly and logs it."""
        self.assertEqual(self.agent_btc.symbol, "BTC-USD")
        self.assertEqual(self.agent_btc.mode, "learning")
        self.assertTrue(os.path.exists(TRADER_LOG_FILE))
        with open(TRADER_LOG_FILE, "r") as f:
            log_content = f.read()
        self.assertIn(
            f'"symbol": "BTC-USD", "mode": "learning"',
            log_content,
        )

    @patch("requests.get")
    def test_get_current_price_success(self, mock_get):
        """Test successful price fetching from the API."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"amount": "50000.78"}}
        mock_get.return_value = mock_response

        price = self.agent_btc.get_current_price()

        self.assertEqual(price, 50000.78)
        mock_get.assert_called_once_with(
            "https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=10
        )
        self.assertTrue(os.path.exists(TRADER_DATA_JSON_FILE))
        with open(TRADER_DATA_JSON_FILE, "r") as f:
            data = json.load(f)
        self.assertEqual(data["price"], 50000.78)

    @patch("requests.get")
    def test_get_current_price_http_error(self, mock_get):
        """Test handling of an HTTP error during price fetching."""
        mock_response = MagicMock()
        http_error = requests.exceptions.HTTPError(response=MagicMock(status_code=404))
        mock_response.raise_for_status.side_effect = http_error
        mock_get.return_value = mock_response

        price = self.agent_btc.get_current_price()

        self.assertIsNone(price)
        with open(TRADER_LOG_FILE, "r") as f:
            log_content = f.read()
        self.assertIn("Could not fetch price for BTC-USD: HTTP Error 404", log_content)

    @patch("katana.trader_agent.TraderAgent.get_current_price")
    def test_make_decision_with_mocked_price(self, mock_get_current_price):
        """Test the make_decision method with a mocked price."""
        mock_get_current_price.return_value = 52000.00

        self.agent_btc.make_decision()

        self.assertTrue(os.path.exists(DECISIONS_JSON_FILE))
        with open(DECISIONS_JSON_FILE, "r") as f:
            decisions = json.load(f)
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0]["price"], 52000.00)

    @patch("katana.trader_agent.TraderAgent.get_current_price")
    def test_make_decision_on_price_failure(self, mock_get_current_price):
        """Test the make_decision method when price retrieval fails."""
        mock_get_current_price.return_value = None

        self.agent_btc.make_decision()

        self.assertFalse(os.path.exists(DECISIONS_JSON_FILE))
        with open(TRADER_LOG_FILE, "r") as f:
            log_content = f.read()
        self.assertIn("Decision aborted for BTC-USD", log_content)


if __name__ == "__main__":
    unittest.main()
