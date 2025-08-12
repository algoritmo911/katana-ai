from unittest.mock import patch, MagicMock
import requests
from katana.exchange.coinbase_api import get_spot_price

@patch('katana.exchange.coinbase_api.requests.get')
def test_get_spot_price_success(mock_get, caplog):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": {"amount": "50000.75", "currency": "USD"}}
    mock_get.return_value = mock_response

    price = get_spot_price("BTC-USD")
    assert price == 50000.75
    mock_get.assert_called_once_with("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=10)

    assert "Requesting spot price for BTC-USD" in caplog.text
    assert "Successfully fetched spot price for BTC-USD: 50000.75" in caplog.text

@patch('katana.exchange.coinbase_api.requests.get')
def test_get_spot_price_http_error(mock_get, caplog):
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = "Not Found"
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Client Error: Not Found")
    mock_get.return_value = mock_response

    price = get_spot_price("INVALID-PAIR")
    assert price is None

    assert "Requesting spot price for INVALID-PAIR" in caplog.text
    assert "HTTP error occurred while fetching price for INVALID-PAIR" in caplog.text
    assert "404 Client Error: Not Found" in caplog.text

@patch('katana.exchange.coinbase_api.requests.get')
def test_get_spot_price_connection_error(mock_get, caplog):
    mock_get.side_effect = requests.exceptions.ConnectionError("Failed to connect")

    price = get_spot_price("BTC-USD")
    assert price is None

    assert "Connection error occurred while fetching price for BTC-USD: Failed to connect" in caplog.text

@patch('katana.exchange.coinbase_api.requests.get')
def test_get_spot_price_timeout_error(mock_get, caplog):
    mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

    price = get_spot_price("BTC-USD")
    assert price is None

    assert "Timeout error occurred while fetching price for BTC-USD: Request timed out" in caplog.text

@patch('katana.exchange.coinbase_api.requests.get')
def test_get_spot_price_missing_data_in_response(mock_get, caplog):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": {"currency": "USD"}} # Missing 'amount'
    mock_get.return_value = mock_response

    price = get_spot_price("BTC-USD")
    assert price is None

    assert "Price data not found in response for BTC-USD" in caplog.text

@patch('katana.exchange.coinbase_api.requests.get')
def test_get_spot_price_invalid_price_format_in_response(mock_get, caplog):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": {"amount": "not_a_number", "currency": "USD"}}
    mock_get.return_value = mock_response

    price = get_spot_price("BTC-USD")
    assert price is None

    assert "Error converting price to float for BTC-USD. Price string: 'not_a_number'" in caplog.text
