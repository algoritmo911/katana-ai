import pytest
from unittest.mock import MagicMock, patch
from katana.trader_agent import TraderAgent


@pytest.fixture
def mocked_market_data():
    return {"symbol": "BTC", "price": 30000}


def test_trader_agent_makes_trade_decision(monkeypatch, mocked_market_data):
    agent = TraderAgent(symbol="BTC-USD")

    monkeypatch.setattr(agent, "get_current_price", lambda: mocked_market_data["price"])

    with patch("builtins.print") as mock_print:
        agent.make_decision()
        mock_print.assert_called()
