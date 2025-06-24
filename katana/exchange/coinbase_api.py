import requests
import logging
import os
from decimal import Decimal, InvalidOperation

# --- Logger Setup for Coinbase API ---
LOG_DIR = "logs"
COINBASE_LOG_FILE = os.path.join(LOG_DIR, "coinbase.log")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Future use: load secrets for authenticated requests
# from katana.utils.secrets import get_secret # Assuming a utility function

coinbase_logger = logging.getLogger('KatanaCoinbaseAPI')
coinbase_logger.setLevel(logging.INFO)

# Prevent adding multiple handlers if called multiple times
if not coinbase_logger.hasHandlers():
    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(message)s')

    # File Handler for coinbase.log
    fh = logging.FileHandler(COINBASE_LOG_FILE)
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    coinbase_logger.addHandler(fh)

    # Optional: Console Handler for coinbase logs
    # ch = logging.StreamHandler()
    # ch.setLevel(logging.INFO)
    # ch.setFormatter(formatter)
    # coinbase_logger.addHandler(ch)

COINBASE_API_BASE_URL = "https://api.coinbase.com/v2"

def get_spot_price(pair: str = "BTC-USD") -> float | None:
    """
    Fetches the current spot price for a given pair from Coinbase API.
    Example: get_spot_price("BTC-USD")
    Returns the price as a float, or None if an error occurs.
    """
    url = f"{COINBASE_API_BASE_URL}/prices/{pair}/spot"
    coinbase_logger.info(f"Requesting spot price for {pair} from {url}")

    try:
        response = requests.get(url, timeout=10) # 10 second timeout
        response.raise_for_status() # Raises HTTPError for bad responses (4XX or 5XX)

        data = response.json()
        price_str = data.get("data", {}).get("amount")

        if price_str is None:
            coinbase_logger.error(f"Price data not found in response for {pair}. Response: {data}")
            return None

        price = float(Decimal(price_str)) # Use Decimal for precision then convert
        coinbase_logger.info(f"Successfully fetched spot price for {pair}: {price}")
        return price

    except requests.exceptions.HTTPError as http_err:
        coinbase_logger.error(f"HTTP error occurred while fetching price for {pair}: {http_err} - Response: {response.text}")
        return None
    except requests.exceptions.ConnectionError as conn_err:
        coinbase_logger.error(f"Connection error occurred while fetching price for {pair}: {conn_err}")
        return None
    except requests.exceptions.Timeout as timeout_err:
        coinbase_logger.error(f"Timeout error occurred while fetching price for {pair}: {timeout_err}")
        return None
    except requests.exceptions.RequestException as req_err:
        coinbase_logger.error(f"An unexpected error occurred with requests module for {pair}: {req_err}")
        return None
    except (InvalidOperation, ValueError) as val_err: # Handle issues with Decimal conversion or float()
        coinbase_logger.error(f"Error converting price to float for {pair}. Price string: '{price_str}'. Error: {val_err}")
        return None
    except Exception as e:
        coinbase_logger.error(f"An unexpected error occurred while fetching price for {pair}: {e}")
        return None

def get_authenticated_client():
    """
    Returns an authenticated Coinbase client.
    Placeholder for future implementation requiring API keys.
    """
    # Example of how it might look:
    # api_key = get_secret("coinbase", "api_key")
    # api_secret = get_secret("coinbase", "api_secret")
    # client = CoinbaseClient(api_key, api_secret) # Assuming a CoinbaseClient class
    # return client
    coinbase_logger.info("get_authenticated_client() called, but it's a placeholder for future use.")
    return None

if __name__ == '__main__':
    coinbase_logger.info("Running Coinbase API direct examples...")

    # Test BTC-USD
    btc_price = get_spot_price("BTC-USD")
    if btc_price is not None:
        print(f"Current BTC-USD Price: {btc_price}")
    else:
        print("Failed to fetch BTC-USD price.")

    # Test ETH-USD
    eth_price = get_spot_price("ETH-USD")
    if eth_price is not None:
        print(f"Current ETH-USD Price: {eth_price}")
    else:
        print("Failed to fetch ETH-USD price.")

    # Test an invalid pair to see error handling
    invalid_price = get_spot_price("INVALID-PAIR")
    if invalid_price is None:
        print("Correctly failed to fetch price for INVALID-PAIR.")

    get_authenticated_client()
    coinbase_logger.info("Coinbase API direct examples finished.")
