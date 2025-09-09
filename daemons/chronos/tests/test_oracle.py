import pytest
import json
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from daemons.chronos.db import create_tickers_table, insert_ticker_data
from daemons.chronos.models import TickerData
from daemons.chronos.main import coinbase_websocket_handler
from datetime import datetime

@pytest.fixture
def mock_db_conn():
    """Fixture to create a mock database connection."""
    conn = MagicMock()
    conn.cursor.return_value = MagicMock()
    conn.cursor.return_value.__enter__.return_value = conn.cursor.return_value
    return conn

def test_create_tickers_table(mock_db_conn):
    """
    Tests that the create_tickers_table function executes the correct SQL.
    """
    create_tickers_table(mock_db_conn)
    mock_db_conn.cursor.assert_called_once()
    cursor = mock_db_conn.cursor()
    cursor.execute.assert_called_once()
    sql = cursor.execute.call_args[0][0]
    assert "CREATE TABLE IF NOT EXISTS tickers" in sql
    assert "TIMESTAMP(ts)" in sql
    mock_db_conn.commit.assert_called_once()

def test_insert_ticker_data(mock_db_conn):
    """
    Tests that insert_ticker_data executes the correct SQL with the correct parameters.
    """
    sample_time = datetime.now()
    ticker = TickerData(
        type="ticker", sequence=123, product_id="BTC-USD", price=50000.0,
        open_24h=49000.0, volume_24h=1000.0, low_24h=48000.0, high_24h=51000.0,
        volume_30d=20000.0, time=sample_time, trade_id=456,
    )
    insert_ticker_data(mock_db_conn, ticker)
    mock_db_conn.cursor.assert_called_once()
    cursor = mock_db_conn.cursor()
    cursor.execute.assert_called_once()
    sql, params = cursor.execute.call_args[0]
    assert "INSERT INTO tickers" in sql
    assert params == ("BTC-USD", 50000.0, 1000.0, sample_time)
    mock_db_conn.commit.assert_called_once()

@pytest.mark.asyncio
@patch('daemons.chronos.main.websockets.connect')
@patch('daemons.chronos.main.insert_ticker_data')
async def test_coinbase_handler_success(mock_insert, mock_ws_connect):
    """
    Tests the happy path of the coinbase_websocket_handler.
    """
    # --- Mock Setup ---
    ticker_payload = {
        "type": "ticker", "sequence": 1, "product_id": "BTC-USD", "price": "50000.00",
        "open_24h": "49000.00", "volume_24h": "1000.00", "low_24h": "48000.00", "high_24h": "51000.00",
        "volume_30d": "20000.00", "best_bid": "49999.00", "best_ask": "50001.00", "side": "buy",
        "time": "2023-05-30T10:00:00.123456Z", "trade_id": 1, "last_size": "1.0"
    }

    # Mock the WebSocket object that the context manager returns
    mock_ws = AsyncMock()
    mock_ws.send = AsyncMock()
    # Configure recv to return one message, then raise an error to break the loop
    mock_ws.recv.side_effect = [json.dumps(ticker_payload), asyncio.TimeoutError]

    # Mock the async context manager itself
    async_mock_context_manager = AsyncMock()
    async_mock_context_manager.__aenter__.return_value = mock_ws
    mock_ws_connect.return_value = async_mock_context_manager

    # Mock NATS and DB clients
    mock_nats_client = AsyncMock()
    mock_db = MagicMock()

    # --- Run the handler ---
    # The handler has an infinite loop, so we run it as a task and cancel it
    # after it has had a chance to process the single message.
    handler_task = asyncio.create_task(coinbase_websocket_handler(mock_nats_client, mock_db))
    await asyncio.sleep(0.1)
    handler_task.cancel()
    try:
        await handler_task
    except asyncio.CancelledError:
        pass

    # --- Assertions ---
    mock_ws.send.assert_awaited_once()
    mock_insert.assert_called_once()
    mock_nats_client.publish.assert_awaited_once()

    subject = mock_nats_client.publish.call_args[0][0]
    payload = json.loads(mock_nats_client.publish.call_args[0][1].decode())
    assert subject == "chronos.market.ticker.BTC-USD"
    assert payload["price"] == 50000.0
