import logging
import time
from typing import Optional
from katana.logging_config import setup_logging
from katana_agent import KatanaAgent
from katana.exchange.coinbase_api import get_spot_price
from katana.memory.core import MemoryCore

# Get a module-specific logger, child of 'katana'
logger = logging.getLogger('katana.bot')

class KatanaBot:
    def __init__(self, bot_name="KatanaBot", memory: Optional[MemoryCore] = None):
        self.name = bot_name
        self.memory = memory
        # The bot itself now has an agent, which is a more general component.
        # This agent doesn't have tools by default, it's for high-level tasks.
        self.agent = KatanaAgent(
            name=f"{self.name}-SubAgent",
            role="A general sub-agent for the main bot.",
            memory=self.memory
        )
        logger.info("KatanaBot '%s' initialized with agent '%s'.", self.name, self.agent.name)

    def start_mission(self, mission_name: str):
        """
        Starts a mission by delegating it to the bot's internal agent.
        """
        logger.debug("Bot '%s' starting mission: %s", self.name, mission_name)
        if not mission_name:
            logger.error("Mission name cannot be empty for bot '%s'.", self.name)
            return

        # We now call 'execute' with a structured task
        task = {
            "action": "execute_mission",
            "mission_name": mission_name
        }
        # The default agent doesn't have an 'execute_mission' tool, so this will currently fail
        # but it demonstrates the new interaction pattern.
        self.agent.execute(task)
        logger.info("Bot '%s' mission '%s' underway.", self.name, mission_name)

    def GREETING(self): # Keep existing method for compatibility with old test
        logger.debug("Bot '%s' GREETING method called.", self.name)
        return f"Hello from {self.name}!"

    def handle_command(self, command_string: str, user_id: str):
        start_time = time.time()
        logger.info(f"Bot '{self.name}' received command: '{command_string}' from user_id: {user_id}")
        parts = command_string.strip().lower().split()
        if not parts:
            logger.warning("Empty command received.")
            return f"{self.name}: Empty command."

        command = parts[0]
        args = parts[1:]
        response_message = ""
        success = False

        if command == "!price":
            if len(args) == 1:
                pair = args[0].upper() # e.g., btc-usd -> BTC-USD
                logger.info(f"Attempting to fetch price for pair: {pair} via command.")
                price = get_spot_price(pair)
                if price is not None:
                    response_message = f"{self.name}: Current price for {pair}: {price} (currency from pair)"
                    logger.info(f"Successfully generated price message for {pair}: {price}")
                    success = True
                else:
                    response_message = f"{self.name}: Could not fetch price for {pair}. See server logs for details."
                    logger.warning(f"Failed to fetch price for {pair} via command.")
            else:
                error_msg = "!price command requires one argument (the trading pair). Usage: !price BTC-USD"
                logger.warning(error_msg)
                response_message = f"{self.name}: {error_msg}"
        elif command == "!greet":
            greeting_message = self.GREETING()
            response_message = f"{self.name}: {greeting_message}"
            logger.info("Executed !greet command.")
            success = True
        else:
            unknown_cmd_msg = f"Unknown command '{command}'. Try !price BTC-USD or !greet."
            logger.warning(f"Unknown command received: {command}")
            response_message = f"{self.name}: {unknown_cmd_msg}"

        duration = time.time() - start_time
        if self.memory:
            # The dialogue logging remains unchanged.
            self.memory.add_dialogue(
                user_id=user_id,
                command_name=command,
                input_data={"command_string": command_string},
                output_data={"response": response_message},
                duration=duration,
                success=success,
                tags=[command]
            )

        return response_message
