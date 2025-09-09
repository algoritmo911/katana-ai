import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from daemons.hephaestus.main import HephaestusDaemon

@pytest.fixture
def mock_doppler():
    """Fixture to mock the DopplerSDK."""
    with patch('daemons.hephaestus.main.DopplerSDK') as mock_sdk:
        mock_instance = mock_sdk.return_value
        mock_instance.secrets.list.return_value = {
            "COINBASE_API_KEY": {"computed": "test_api_key"},
            "COINBASE_API_SECRET": {"computed": "test_api_secret"}
        }
        yield mock_sdk

@pytest.fixture
def mock_coinbase_client():
    """Fixture to mock the CoinbaseAdvancedClient."""
    with patch('daemons.hephaestus.main.CoinbaseAdvancedClient') as mock_client:
        mock_instance = mock_client.return_value
        mock_instance.place_market_order = AsyncMock(return_value={"status": "SUCCESS", "order_id": "mock-123"})
        yield mock_client

@pytest.mark.asyncio
async def test_message_handler_success(mock_doppler, mock_coinbase_client):
    """
    Tests the successful handling of a 'hephaestus.trade' action command.
    """
    # --- Setup ---
    daemon = HephaestusDaemon()
    daemon.get_secrets() # Run sync part to set secrets
    daemon.coinbase_client = mock_coinbase_client.return_value
    daemon.nats_client = AsyncMock()

    # Create a mock NATS message
    agent_id = "test-agent-001"
    action_payload = {
        "type": "hephaestus.trade",
        "parameters": {
            "action": "BUY",
            "product_id": "BTC-USD",
            "amount": "0.01"
        }
    }
    mock_msg = MagicMock()
    mock_msg.subject = f"agent.{agent_id}.action.execute"
    mock_msg.data = json.dumps(action_payload).encode()

    # --- Run ---
    await daemon.message_handler(mock_msg)

    # --- Assertions ---
    # 1. Assert that the Coinbase client was called correctly
    daemon.coinbase_client.place_market_order.assert_awaited_once_with(
        product_id="BTC-USD",
        side="BUY",
        size=0.01
    )

    # 2. Assert that the result was published to NATS correctly
    daemon.nats_client.publish.assert_awaited_once()
    result_subject = daemon.nats_client.publish.call_args[0][0]
    result_payload = json.loads(daemon.nats_client.publish.call_args[0][1].decode())

    assert result_subject == f"agent.{agent_id}.action.result"
    assert result_payload["status"] == "SUCCESS"
    assert result_payload["details"]["order_id"] == "mock-123"
