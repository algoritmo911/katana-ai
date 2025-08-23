# ops/heartbeat.py
import asyncio
from datetime import datetime, timezone
from loguru import logger

HEARTBEAT_FILE_PATH = "/tmp/katana_heartbeat.txt"
HEARTBEAT_INTERVAL_SECONDS = 30

async def run_heartbeat():
    """Periodically updates a heartbeat file to signal liveness."""
    logger.info("Heartbeat process started.")
    while True:
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            with open(HEARTBEAT_FILE_PATH, "w") as f:
                f.write(timestamp)
            # logger.debug(f"Heartbeat updated at {timestamp}")
        except Exception as e:
            logger.error(f"Failed to write heartbeat file: {e}")
        await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
