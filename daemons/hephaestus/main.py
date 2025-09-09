import asyncio
import json
import logging
import os
import nats
from dopplersdk import DopplerSDK
from katana_ai.adapters.coinbase_advanced_client import CoinbaseAdvancedClient

# --- Configuration ---
LOG_LEVEL = logging.INFO
NATS_URL = "nats://localhost:4222"
NATS_SUBJECT = "agent.*.action.execute"
NATS_QUEUE_GROUP = "hephaestus_forge"

# Configure logging
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)


class HephaestusDaemon:
    def __init__(self):
        self.nats_client = None
        self.coinbase_client = None
        self.doppler = DopplerSDK()
        # The service token is expected to be in the DOPPLER_TOKEN env var
        if not os.getenv("DOPPLER_TOKEN"):
            logger.warning("DOPPLER_TOKEN not set. Hephaestus may not be able to get secrets.")

    def get_secrets(self):
        """Fetches secrets from Doppler."""
        try:
            # This is a blocking call, should be run before the async loop
            secrets = self.doppler.secrets.list(project="katana-ai", config="prd")
            # Assuming secrets are named COINBASE_API_KEY and COINBASE_API_SECRET in Doppler
            api_key = secrets.get("COINBASE_API_KEY", {}).get("computed")
            api_secret = secrets.get("COINBASE_API_SECRET", {}).get("computed")
            if not api_key or not api_secret:
                raise ValueError("Coinbase secrets not found in Doppler.")
            # Set them as environment variables for the Coinbase client to pick up
            os.environ["COINBASE_API_KEY"] = api_key
            os.environ["COINBASE_API_SECRET"] = api_secret
            logger.info("Successfully fetched and set Coinbase secrets from Doppler.")
            return True
        except Exception as e:
            logger.error(f"Failed to get secrets from Doppler: {e}")
            logger.warning("Falling back to .env file for secrets if available.")
            return False

    async def message_handler(self, msg):
        """Handles incoming action commands."""
        subject = msg.subject
        try:
            agent_id = subject.split('.')[1]
            data = json.loads(msg.data.decode())
            action_type = data.get("type")
            params = data.get("parameters", {})

            logger.info(f"Received action '{action_type}' for agent '{agent_id}' with params: {params}")

            result_payload = {}
            if action_type == "hephaestus.trade":
                trade_result = await self.coinbase_client.place_market_order(
                    product_id=params.get("product_id"),
                    side=params.get("action"),
                    size=float(params.get("amount"))
                )
                result_payload = {"status": "SUCCESS", "details": trade_result}
            else:
                result_payload = {"status": "FAILURE", "error": f"Unknown action type: {action_type}"}

            # Publish the result
            result_subject = f"agent.{agent_id}.action.result"
            await self.nats_client.publish(result_subject, json.dumps(result_payload).encode())
            logger.info(f"Published result for agent '{agent_id}' to '{result_subject}'")

        except Exception as e:
            logger.error(f"Error processing message from subject '{subject}': {e}", exc_info=True)


    async def run(self):
        """Connects to NATS and starts listening for messages."""
        self.get_secrets()
        self.coinbase_client = CoinbaseAdvancedClient()

        try:
            self.nats_client = await nats.connect(NATS_URL)
            logger.info("Connected to NATS.")
            await self.nats_client.subscribe(NATS_SUBJECT, queue=NATS_QUEUE_GROUP, cb=self.message_handler)
            logger.info(f"Subscribed to '{NATS_SUBJECT}' on queue '{NATS_QUEUE_GROUP}'.")

            # Keep the daemon running
            while True:
                await asyncio.sleep(1)
        except Exception as e:
            logger.critical(f"Hephaestus daemon failed critically: {e}")
        finally:
            if self.nats_client:
                await self.nats_client.close()

if __name__ == "__main__":
    daemon = HephaestusDaemon()
    try:
        asyncio.run(daemon.run())
    except KeyboardInterrupt:
        logger.info("Hephaestus daemon stopped.")
