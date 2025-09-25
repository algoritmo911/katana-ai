import requests
import logging
import os
from decimal import Decimal, InvalidOperation

LOG_DIR = "logs"
COINBASE_LOG_FILE = os.path.join(LOG_DIR, "coinbase.log")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

coinbase_logger = logging.getLogger("KatanaCoinbaseAPI")
coinbase_logger.setLevel(logging.INFO)

if not coinbase_logger.hasHandlers():
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(message)s"
    )

    fh = logging.FileHandler(COINBASE_LOG_FILE)
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    coinbase_logger.addHandler(fh)

COINBASE_API_BASE_URL = "https://api.coinbase.com/v2"

def get_spot_price(pair: str = "BTC-USD") -> float | None:
    """
    Fetches the current spot price for a given pair from Coinbase API.
    """
    url = f"{COINBASE_API_BASE_URL}/prices/{pair}/spot"
    coinbase_logger.info(f"Requesting spot price for {pair} from {url}")

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()
        price_str = data.get("data", {}).get("amount")

        if price_str is None:
            coinbase_logger.error(
                f"Price data not found in response for {pair}. Response: {data}"
            )
            return None

        price = float(Decimal(price_str))
        coinbase_logger.info(f"Successfully fetched spot price for {pair}: {price}")
        return price

    except requests.exceptions.HTTPError as http_err:
        coinbase_logger.error(
            f"HTTP error occurred while fetching price for {pair}: {http_err} - Response: {response.text}"
        )
        return None
    except requests.exceptions.ConnectionError as conn_err:
        coinbase_logger.error(
            f"Connection error occurred while fetching price for {pair}: {conn_err}"
        )
        return None
    except requests.exceptions.Timeout as timeout_err:
        coinbase_logger.error(
            f"Timeout error occurred while fetching price for {pair}: {timeout_err}"
        )
        return None
    except requests.exceptions.RequestException as req_err:
        coinbase_logger.error(
            f"An unexpected error occurred with requests module for {pair}: {req_err}"
        )
        return None
    except (
        InvalidOperation,
        ValueError,
    ) as val_err:
        coinbase_logger.error(
            f"Error converting price to float for {pair}. Price string: '{price_str}'. Error: {val_err}"
        )
        return None
    except Exception as e:
        coinbase_logger.error(
            f"An unexpected error occurred while fetching price for {pair}: {e}"
        )
        return None

def get_authenticated_client():
    """
    Returns an authenticated Coinbase client.
    Placeholder for future implementation requiring API keys.
    """
    coinbase_logger.info(
        "get_authenticated_client() called, but it's a placeholder for future use."
    )
    return None


if __name__ == "__main__":
    coinbase_logger.info("Running Coinbase API direct examples...")

    btc_price = get_spot_price("BTC-USD")
    if btc_price is not None:
        print(f"Current BTC-USD Price: {btc_price}")
    else:
        print("Failed to fetch BTC-USD price.")

    eth_price = get_spot_price("ETH-USD")
    if eth_price is not None:
        print(f"Current ETH-USD Price: {eth_price}")
    else:
        print("Failed to fetch ETH-USD price.")

    invalid_price = get_spot_price("INVALID-PAIR")
    if invalid_price is None:
        print("Correctly failed to fetch price for INVALID-PAIR.")

    get_authenticated_client()
    coinbase_logger.info("Coinbase API direct examples finished.")
