import logging
from katana.bots.base_bot import BaseBot
from katana.exchange.coinbase_api import get_spot_price

logger = logging.getLogger(__name__)

class KatanaBot(BaseBot):
    def __init__(self, bot_name="KatanaBot", profile=None):
        super().__init__(bot_name, profile)

    def handle_command(self, command_string: str):
        logger.info(f"Bot '{self.name}' received command: {command_string}")
        parts = command_string.strip().lower().split()
        if not parts:
            logger.warning("Empty command received.")
            return f"{self.name}: Empty command."

        command = parts[0]
        args = parts[1:]
        response_message = ""

        if command == "!price":
            if len(args) == 1:
                pair = args[0].upper()
                logger.info(f"Attempting to fetch price for pair: {pair} via command.")
                price = get_spot_price(pair)
                if price is not None:
                    response_message = f"{self.name}: Current price for {pair}: {price}"
                else:
                    response_message = f"{self.name}: Could not fetch price for {pair}."
            else:
                response_message = f"{self.name}: !price command requires one argument (e.g., !price BTC-USD)"
        elif command == "!greet":
            response_message = f"Hello from {self.name}!"
        else:
            response_message = f"Unknown command '{command}'."

        return response_message

# The __main__ block is removed as the bot will be run by the FastAPI application (main.py)
# For testing, you would now run main.py and interact via Telegram or API endpoints.
# Example of old main block for reference (now removed):
# if __name__ == '__main__':
#     setup_logging(logging.DEBUG)
#     bot = KatanaBot("MainBot")
#     print("\n--- Testing Bot Commands ---")
#     # Test calls would need to capture print output or be adapted if handle_command returned values
#     # For example: print(bot.handle_command("!price btc-usd"))
#     # bot.handle_command("!price btc-usd")
#     # bot.handle_command("!price eth-eur")
#     # ... and so on
#     print("--- Bot Command Testing Finished ---")
