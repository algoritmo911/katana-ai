"""
Unit tests for the CoinbaseAdvancedClient.
"""
import pytest
import httpx
from unittest.mock import patch, AsyncMock, Mock
from katana_ai.adapters.coinbase_advanced_client import (
    CoinbaseAdvancedClient,
    CoinbaseAPIError,
    CoinbaseForbiddenError,
    CoinbaseRateLimitError,
    CoinbaseInternalServerError,
)


def test_init_success(monkeypatch):
    """
    Tests successful initialization of the CoinbaseAdvancedClient.
    """
    monkeypatch.setenv("COINBASE_API_KEY", "test_key")
    monkeypatch.setenv("COINBASE_API_SECRET", "test_secret")
    client = CoinbaseAdvancedClient()
    assert client.api_key == "test_key"
    assert client.api_secret == "test_secret"


def test_init_missing_credentials(monkeypatch):
    """
    Tests that a ValueError is raised if API credentials are not set.
    """
    monkeypatch.delenv("COINBASE_API_KEY", raising=False)
    monkeypatch.delenv("COINBASE_API_SECRET", raising=False)
    with pytest.raises(ValueError):
        CoinbaseAdvancedClient()


@patch('time.time', return_value=1672531200)
def test_sign_message(mock_time, monkeypatch):
    """
    Tests the _sign_message method.
    """
    monkeypatch.setenv("COINBASE_API_KEY", "test_key")
    monkeypatch.setenv("COINBASE_API_SECRET", "test_secret")
    client = CoinbaseAdvancedClient()
    timestamp, signature = client._sign_message("GET", "/api/v3/brokerage/products")

    expected_signature = "0e523847efdbfa8989049fe2a9f6b9c89be2f10cd2a3b0b74644e1ff8cc8a716"
    assert timestamp == "1672531200"
    assert signature == expected_signature


@pytest.mark.asyncio
@patch('katana_ai.adapters.coinbase_advanced_client.httpx.AsyncClient')
async def test_get_products_success(MockAsyncClient, monkeypatch):
    """
    Tests successful call to get_products.
    """
    monkeypatch.setenv("COINBASE_API_KEY", "test_key")
    monkeypatch.setenv("COINBASE_API_SECRET", "test_secret")

    mock_response = Mock(spec=httpx.Response)
    mock_response.json.return_value = {"products": [{"product_id": "BTC-USD"}]}
    mock_response.raise_for_status.return_value = None

    mock_async_client_instance = AsyncMock()
    mock_async_client_instance.get.return_value = mock_response
    MockAsyncClient.return_value = mock_async_client_instance

    client = CoinbaseAdvancedClient()

    with patch('time.time', return_value=1672531200):
        products = await client.get_products()

        expected_headers = client._get_auth_headers("GET", "/api/v3/brokerage/products")
        mock_async_client_instance.get.assert_called_once_with(
            "/api/v3/brokerage/products", headers=expected_headers
        )
        assert products == {"products": [{"product_id": "BTC-USD"}]}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status_code, error_text, expected_exception",
    [
        (403, "Forbidden", CoinbaseForbiddenError),
        (429, "Rate limit exceeded", CoinbaseRateLimitError),
        (500, "Internal server error", CoinbaseInternalServerError),
        (404, "Not Found", CoinbaseAPIError),
    ],
)
@patch('katana_ai.adapters.coinbase_advanced_client.httpx.AsyncClient')
async def test_get_products_errors(
    MockAsyncClient, monkeypatch, status_code, error_text, expected_exception
):
    """
    Tests that get_products raises the correct exception for various error codes.
    """
    monkeypatch.setenv("COINBASE_API_KEY", "test_key")
    monkeypatch.setenv("COINBASE_API_SECRET", "test_secret")

    mock_request = httpx.Request("GET", "https://api.coinbase.com/api/v3/brokerage/products")
    mock_response = httpx.Response(status_code=status_code, text=error_text, request=mock_request)

    http_error = httpx.HTTPStatusError(
        message=f"{status_code} Client Error", request=mock_request, response=mock_response
    )

    mock_response_from_get = Mock(spec=httpx.Response)
    mock_response_from_get.raise_for_status.side_effect = http_error

    mock_async_client_instance = AsyncMock()
    mock_async_client_instance.get.return_value = mock_response_from_get
    MockAsyncClient.return_value = mock_async_client_instance

    client = CoinbaseAdvancedClient()

    with pytest.raises(expected_exception) as excinfo:
        await client.get_products()

    assert error_text in str(excinfo.value)
