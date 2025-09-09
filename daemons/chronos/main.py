import asyncio
import json
import logging
import time
import nats
import websockets
from pydantic import ValidationError

from .db import get_db_connection, create_tickers_table, insert_ticker_data
from .models import TickerData

# --- Configuration ---
LOG_LEVEL = logging.INFO
COINBASE_WS_URL = "wss://ws-feed.pro.coinbase.com"
NATS_URL = "nats://localhost:4222"
PRODUCT_IDS = ["BTC-USD", "ETH-USD"]

# Configure logging
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)


async def coinbase_websocket_handler(nats_client, db_conn):
    """Handles the WebSocket connection to Coinbase."""
    subscribe_payload = {
        "type": "subscribe",
        "product_ids": PRODUCT_IDS,
        "channels": ["ticker"],
    }
    while True:
        try:
            async with websockets.connect(COINBASE_WS_URL) as ws:
                await ws.send(json.dumps(subscribe_payload))
                logger.info(f"Connected to Coinbase WebSocket and subscribed to {PRODUCT_IDS}.")

                while True:
                    message = await ws.recv()
                    data = json.loads(message)

                    if data.get("type") == "ticker":
                        try:
                            ticker = TickerData(**data)

                            # 1. Insert into DB
                            insert_ticker_data(db_conn, ticker)

                            # 2. Publish to NATS
                            subject = f"chronos.market.ticker.{ticker.product_id}"
                            payload = ticker.model_dump_json().encode()
                            await nats_client.publish(subject, payload)
                            logger.debug(f"Processed and published ticker for {ticker.product_id}")

                        except ValidationError as e:
                            logger.warning(f"Failed to validate ticker data: {e}")
                        except Exception as e:
                            logger.error(f"Error processing ticker message: {e}")

        except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError) as e:
            logger.error(f"Coinbase WebSocket connection error: {e}. Reconnecting in 10 seconds...")
            await asyncio.sleep(10)
        except Exception as e:
            logger.error(f"An unexpected error occurred in WebSocket handler: {e}")
            await asyncio.sleep(10)


async def heartbeat_publisher(nats_client):
    """Publishes a heartbeat to NATS every second."""
    while True:
        await nats_client.publish("chronos.tick.1s", str(time.time()).encode())
        await asyncio.sleep(1)


async def main():
    """Main entry point for the Chronos daemon."""
    nats_client = None
    db_conn = None

    try:
        # Connect to services
        nats_client = await nats.connect(NATS_URL)
        logger.info("Connected to NATS.")

        db_conn = get_db_connection()
        create_tickers_table(db_conn)

        # Start background tasks
        heartbeat_task = asyncio.create_task(heartbeat_publisher(nats_client))
        websocket_task = asyncio.create_task(coinbase_websocket_handler(nats_client, db_conn))

        logger.info("Chronos daemon started with heartbeat and WebSocket handlers.")
        await asyncio.gather(heartbeat_task, websocket_task)

    except Exception as e:
        logger.critical(f"Chronos daemon failed critically: {e}")
    finally:
        if nats_client:
            await nats_client.close()
        if db_conn:
            db_conn.close()
        logger.info("Chronos daemon shut down.")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Chronos daemon stopped by user.")
