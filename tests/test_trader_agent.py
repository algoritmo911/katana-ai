import unittest
from unittest.mock import MagicMock, patch
from katana.trader_agent import TraderAgent


class TraderAgentTests(unittest.TestCase):
    def test_trader_agent_makes_trade_decision(self):
        agent = TraderAgent(symbol="BTC-USD")
        mocked_market_data = {"symbol": "BTC", "price": 30000}

        agent.get_current_price = lambda: mocked_market_data["price"]

        with patch("builtins.print") as mock_print:
            agent.make_decision()
            mock_print.assert_called()


if __name__ == "__main__":
    unittest.main()
