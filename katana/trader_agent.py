import logging
import os

# import random # Removed as it's no longer needed
import requests
import json
from datetime import datetime, timezone

# --- Logger Setup ---
LOG_DIR = "logs"
TRADER_LOG_FILE = os.path.join(LOG_DIR, "trader.log")
TRADER_DATA_LOG_FILE = os.path.join(LOG_DIR, "trader_data.log")
TRADER_DATA_JSON_FILE = os.path.join(LOG_DIR, "trader_data.json")
DECISIONS_JSON_FILE = os.path.join(LOG_DIR, "decisions.json")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# General Trader Agent Logger
trader_logger = logging.getLogger("KatanaTrader")
trader_logger.setLevel(logging.INFO)
if not trader_logger.hasHandlers():  # Check if handlers already exist
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    fh = logging.FileHandler(TRADER_LOG_FILE)
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    trader_logger.addHandler(fh)

# Trader Data Logger (for API interactions)
trader_data_logger = logging.getLogger("KatanaTraderData")
trader_data_logger.setLevel(logging.INFO)
if not trader_data_logger.hasHandlers():  # Check if handlers already exist
    data_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    dfh = logging.FileHandler(TRADER_DATA_LOG_FILE)
    dfh.setLevel(logging.INFO)
    dfh.setFormatter(data_formatter)
    trader_data_logger.addHandler(dfh)


class TraderAgent:
    def __init__(self, symbol="BTC-USD", mode="learning"):
        self.symbol = symbol
        self.mode = mode
        trader_logger.info(
            f"INITIALIZATION: {json.dumps({'symbol': self.symbol, 'mode': self.mode})}"
        )

    def get_current_price(self) -> float | None:
        """
        Fetches the current spot price for the agent's symbol from CoinBase API.
        Logs API interaction and saves latest price to a JSON file.
        Returns the price as a float, or None if an error occurs.
        """
        api_url = f"https://api.coinbase.com/v2/prices/{self.symbol}/spot"
        trader_data_logger.info(
            f"Attempting to fetch price for {
                self.symbol} from {api_url}"
        )
        response_text_for_error_logging = ""

        try:
            response = requests.get(api_url, timeout=10)
            response_text_for_error_logging = response.text
            response.raise_for_status()

            data = response.json()
            trader_data_logger.info(
                f"CoinBase API response for {
                    self.symbol}: {
                    json.dumps(data)}"
            )

            price_str = data.get("data", {}).get("amount")
            if price_str is None:
                trader_data_logger.error(
                    f"Price amount not found in CoinBase API response for {
                        self.symbol}. Data: {
                        json.dumps(data)}"
                )
                trader_logger.error(
                    f"Could not parse price for {
                        self.symbol}: 'amount' field missing in API response."
                )
                return None

            price = float(price_str)
            trader_logger.info(f"Current price for {self.symbol}: {price} USD")

            price_data_to_save = {
                "symbol": self.symbol,
                "price": price,
                # Use timezone.utc for explicit UTC
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            try:
                with open(TRADER_DATA_JSON_FILE, "w") as f_json:
                    json.dump(price_data_to_save, f_json, indent=4)
                trader_data_logger.info(
                    f"Successfully saved latest price for {
                        self.symbol} to {TRADER_DATA_JSON_FILE}"
                )
            except IOError as e:
                trader_data_logger.error(
                    f"Failed to write latest price to {TRADER_DATA_JSON_FILE}: {e}"
                )

            return price

        except requests.exceptions.Timeout:
            trader_data_logger.error(
                f"Timeout while fetching price for {
                    self.symbol} from {api_url}."
            )
            trader_logger.error(
                f"Could not fetch price for {
                    self.symbol}: Timeout."
            )
        except requests.exceptions.HTTPError as e:
            trader_data_logger.error(
                f"HTTP error for {
                    self.symbol} ({api_url}): {e}. Response: {response_text_for_error_logging}"
            )
            trader_logger.error(
                f"Could not fetch price for {
                    self.symbol}: HTTP Error {
                    e.response.status_code if e.response else 'Unknown'}."
            )
        except requests.exceptions.RequestException as e:
            trader_data_logger.error(
                f"Request exception while fetching price for {
                    self.symbol} ({api_url}): {e}"
            )
            trader_logger.error(
                f"Could not fetch price for {
                    self.symbol}: Network error."
            )
        except json.JSONDecodeError as e:
            trader_data_logger.error(
                f"Error parsing CoinBase API JSON response for {
                    self.symbol} ({api_url}): {e}. Response text: {response_text_for_error_logging}"
            )
            trader_logger.error(
                f"Could not parse price for {
                    self.symbol}: Invalid JSON response from API."
            )
        except (KeyError, ValueError) as e:
            trader_data_logger.error(
                f"Error processing CoinBase API response data for {
                    self.symbol} ({api_url}): {e}. Data: {response_text_for_error_logging}"
            )
            trader_logger.error(
                f"Could not parse price for {
                    self.symbol}: Unexpected data structure or invalid value."
            )

        return None

    def make_decision(self):
        """
        Placeholder for the trading decision logic.
        Logs intent and current learning status.
        """
        trader_logger.info(f"Attempting to make decision for {self.symbol}...")
        current_price = self.get_current_price()

        if current_price is None:
            trader_logger.error(
                f"Decision aborted for {
                    self.symbol} due to failure in retrieving price."
            )
            print(
                f"Trader Agent ({
                    self.symbol}): Could not retrieve current price. See logs in '{LOG_DIR}/' for details."
            )
            return

        trader_logger.info(
            f"Analyzing market for {
                self.symbol}. Current retrieved price: {current_price} USD."
        )

        decision_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbol": self.symbol,
            "price": current_price,
            "decision_type": "observe",  # Placeholder for now
            "confidence": 0.5,  # Placeholder
            "reason": "Initial observation in learning mode.",  # Placeholder
            "mode": self.mode,
        }

        try:
            if (
                os.path.exists(DECISIONS_JSON_FILE)
                and os.path.getsize(DECISIONS_JSON_FILE) > 0
            ):
                with open(DECISIONS_JSON_FILE, "r") as f:
                    decisions_history = json.load(f)
                if not isinstance(decisions_history, list):  # Ensure it's a list
                    decisions_history = []
            else:
                decisions_history = []

            decisions_history.append(decision_record)

            with open(DECISIONS_JSON_FILE, "w") as f:
                json.dump(decisions_history, f, indent=4)
            trader_logger.info(
                f"Decision record for {
                    self.symbol} saved to {DECISIONS_JSON_FILE}"
            )
        except IOError as e:
            trader_logger.error(
                f"Failed to read/write decisions to {DECISIONS_JSON_FILE}: {e}"
            )
        except json.JSONDecodeError as e:
            trader_logger.error(
                f"Failed to decode existing decisions from {DECISIONS_JSON_FILE}: {e}. Overwriting with new decision."
            )
            # Fallback: If JSON is corrupt, overwrite with a list containing
            # the current decision
            with open(DECISIONS_JSON_FILE, "w") as f:
                json.dump([decision_record], f, indent=4)

        log_details = {
            "symbol": self.symbol,
            "price": current_price,
            "mode": self.mode,
            # from decision_record
            "decision_type": decision_record["decision_type"],
            "reason": decision_record["reason"],  # from decision_record
        }

        print_message = ""  # Ensure print_message is defined
        if self.mode == "learning":
            trader_logger.info(
                f"LEARNING_MODE_DECISION: {
                    json.dumps(log_details)}"
            )
            print_message = f"Trader Agent ({
                self.symbol}): Mode: learning. Price: {current_price} USD. Decision: {
                log_details['decision_type']}. See logs."
        elif self.mode == "active":
            trader_logger.info(
                f"ACTIVE_MODE_ACTION_PLACEHOLDER: {
                    json.dumps(log_details)}"
            )
            print_message = f"Trader Agent ({
                self.symbol}): Mode: active. Price: {current_price} USD. Decision: {
                log_details['decision_type']} (placeholder action). See logs."
        else:  # Unknown mode
            trader_logger.warning(
                f"UNKNOWN_MODE_DECISION: {
                    json.dumps(log_details)}. Defaulting to learning behavior."
            )
            print_message = f"Trader Agent ({
                self.symbol}): Mode: unknown ({
                self.mode}). Defaulting to learning. Price: {current_price} USD. See logs."

        print(print_message)


# --- Example Usage (for direct script execution) ---
if __name__ == "__main__":
    # Setup console handlers for direct script execution to see logs in console
    # This allows seeing logs when running `python katana/trader_agent.py`
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Add console handler to trader_logger if not already present (e.g. by an
    # importer)
    if not any(isinstance(h, logging.StreamHandler) for h in trader_logger.handlers):
        ch_trader = logging.StreamHandler()
        ch_trader.setLevel(logging.INFO)
        ch_trader.setFormatter(console_formatter)
        trader_logger.addHandler(ch_trader)

    # Add console handler to trader_data_logger if not already present
    if not any(
        isinstance(h, logging.StreamHandler) for h in trader_data_logger.handlers
    ):
        ch_data = logging.StreamHandler()
        ch_data.setLevel(logging.INFO)
        ch_data.setFormatter(console_formatter)
        trader_data_logger.addHandler(ch_data)

    trader_logger.info(
        "Starting TraderAgent example with real API calls, demonstrating different modes..."
    )

    # BTC example in learning mode (default)
    agent_btc_learn = TraderAgent(symbol="BTC-USD")  # Implicitly learning
    agent_btc_learn.make_decision()

    # ETH example in active mode
    agent_eth_active = TraderAgent(symbol="ETH-USD", mode="active")
    agent_eth_active.make_decision()

    # Example with an invalid mode
    # agent_invalid_mode = TraderAgent(symbol="LTC-USD", mode="unknown_mode_test")
    # agent_invalid_mode.make_decision()

    trader_logger.info("TraderAgent example finished.")
