import unittest
from unittest.mock import patch, MagicMock
import logging
import os
import requests  # Required for requests.exceptions.HTTPError etc.

# Assuming katana.exchange.coinbase_api can be imported.
# This might require PYTHONPATH adjustments (e.g., export PYTHONPATH=.) when running tests.
from katana.exchange.coinbase_api import get_spot_price, COINBASE_LOG_FILE, LOG_DIR

# Ensure the logs directory exists for testing if logs are written
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)


class TestCoinbaseAPI(unittest.TestCase):

    def setUp(self):
        # Clear log file before each test to ensure clean state for log content checks
        if os.path.exists(COINBASE_LOG_FILE):
            os.remove(COINBASE_LOG_FILE)

        # It's good practice to also ensure the logger is clean or reconfigured if needed,
        # but for this scope, clearing the file is the primary concern for content checks.
        # Re-adding handler to the logger to ensure it's active for the test,
        # especially if other tests might clear handlers.
        self.logger = logging.getLogger("KatanaCoinbaseAPI")
        self.logger.setLevel(logging.INFO)  # Ensure level is set for tests

        # Remove existing handlers to avoid duplicate logs if tests run multiple times in same session
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
            handler.close()

        self.file_handler = logging.FileHandler(COINBASE_LOG_FILE)
        self.file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(message)s"
            )
        )
        self.logger.addHandler(self.file_handler)

    def tearDown(self):
        # Clean up log file after tests
        if os.path.exists(COINBASE_LOG_FILE):
            # os.remove(COINBASE_LOG_FILE) # Comment out to inspect logs after test run
            pass
        # Close and remove handler to avoid issues with subsequent tests or file locks
        if self.file_handler:
            self.logger.removeHandler(self.file_handler)
            self.file_handler.close()

    @patch("katana.exchange.coinbase_api.requests.get")
    def test_get_spot_price_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"amount": "50000.75", "currency": "USD"}
        }
        mock_get.return_value = mock_response

        price = get_spot_price("BTC-USD")
        self.assertEqual(price, 50000.75)
        mock_get.assert_called_once_with(
            "https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=10
        )

        with open(COINBASE_LOG_FILE, "r") as f:
            log_content = f.read()
        self.assertIn("Requesting spot price for BTC-USD", log_content)
        self.assertIn(
            "Successfully fetched spot price for BTC-USD: 50000.75", log_content
        )

    @patch("katana.exchange.coinbase_api.requests.get")
    def test_get_spot_price_http_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Client Error: Not Found"
        )
        mock_get.return_value = mock_response

        price = get_spot_price("INVALID-PAIR")
        self.assertIsNone(price)

        with open(COINBASE_LOG_FILE, "r") as f:
            log_content = f.read()
        self.assertIn("Requesting spot price for INVALID-PAIR", log_content)
        self.assertIn(
            "HTTP error occurred while fetching price for INVALID-PAIR", log_content
        )
        self.assertIn("404 Client Error: Not Found", log_content)

    @patch("katana.exchange.coinbase_api.requests.get")
    def test_get_spot_price_connection_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("Failed to connect")

        price = get_spot_price("BTC-USD")
        self.assertIsNone(price)

        with open(COINBASE_LOG_FILE, "r") as f:
            log_content = f.read()
        self.assertIn(
            "Connection error occurred while fetching price for BTC-USD: Failed to connect",
            log_content,
        )

    @patch("katana.exchange.coinbase_api.requests.get")
    def test_get_spot_price_timeout_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

        price = get_spot_price("BTC-USD")
        self.assertIsNone(price)

        with open(COINBASE_LOG_FILE, "r") as f:
            log_content = f.read()
        self.assertIn(
            "Timeout error occurred while fetching price for BTC-USD: Request timed out",
            log_content,
        )

    @patch("katana.exchange.coinbase_api.requests.get")
    def test_get_spot_price_missing_data_in_response(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"currency": "USD"}
        }  # Missing 'amount'
        mock_get.return_value = mock_response

        price = get_spot_price("BTC-USD")
        self.assertIsNone(price)

        with open(COINBASE_LOG_FILE, "r") as f:
            log_content = f.read()
        self.assertIn("Price data not found in response for BTC-USD", log_content)

    @patch("katana.exchange.coinbase_api.requests.get")
    def test_get_spot_price_invalid_price_format_in_response(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"amount": "not_a_number", "currency": "USD"}
        }
        mock_get.return_value = mock_response

        price = get_spot_price("BTC-USD")
        self.assertIsNone(price)

        with open(COINBASE_LOG_FILE, "r") as f:
            log_content = f.read()
        self.assertIn(
            "Error converting price to float for BTC-USD. Price string: 'not_a_number'",
            log_content,
        )


if __name__ == "__main__":
    unittest.main()

# Added import requests - I missed this in the prompt.
