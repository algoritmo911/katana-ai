import logging
import os
import random

# --- Logger Setup ---
LOG_DIR = "logs"
TRADER_LOG_FILE = os.path.join(LOG_DIR, "trader.log")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

trader_logger = logging.getLogger('KatanaTrader')
trader_logger.setLevel(logging.INFO)

# Prevent adding multiple handlers if called multiple times
if not trader_logger.hasHandlers():
    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # File Handler for trader.log
    fh = logging.FileHandler(TRADER_LOG_FILE)
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    trader_logger.addHandler(fh)

    # Optional: Console Handler for trader logs (can be noisy)
    # ch = logging.StreamHandler()
    # ch.setLevel(logging.INFO)
    # ch.setFormatter(formatter)
    # trader_logger.addHandler(ch)

class TraderAgent:
    def __init__(self, symbol="BTC-USD"):
        self.symbol = symbol
        trader_logger.info(f"TraderAgent initialized for symbol: {self.symbol}")

    def get_mock_price(self) -> float:
        """
        Simulates fetching the current price for the agent's symbol.
        Returns a random price for demonstration.
        """
        # In a real scenario, this would call CoinBase API
        # For now, generating a random price between 20000 and 70000 for BTC-USD
        mock_price = round(random.uniform(20000.00, 70000.00), 2)
        trader_logger.info(f"Mock price for {self.symbol}: {mock_price} USD")
        return mock_price

    def make_decision(self):
        """
        Placeholder for the trading decision logic.
        Logs intent and current learning status.
        """
        current_price = self.get_mock_price()

        trader_logger.info(f"Analyzing market for {self.symbol}. Current price: {current_price} USD.")
        # Future decision logic would go here
        # e.g., if current_price > self.buy_threshold: self.place_buy_order()

        trader_logger.info("Trader agent decision logic not fully implemented. Learning mode active.")
        print(f"Trader Agent ({self.symbol}): Learning mode active. Price: {current_price} USD. Check logs/trader.log for details.")

# --- Example Usage (for direct script execution) ---
if __name__ == '__main__':
    trader_logger.info("Starting TraderAgent example...")
    agent = TraderAgent(symbol="BTC-USD")
    agent.make_decision()

    agent_eth = TraderAgent(symbol="ETH-USD")
    agent_eth.make_decision()
    trader_logger.info("TraderAgent example finished.")
