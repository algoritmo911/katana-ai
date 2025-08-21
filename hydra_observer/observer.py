import json
import os
import redis
import logging
from hydra_observer.system_state import system_state
from hydra_observer.analysis import analyze_log

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Redis configuration
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_CHANNEL = os.environ.get("REDIS_CHANNEL", "katana_logs")

def main():
    """Consumes log messages from Redis Pub/Sub and updates the System State Vector."""
    logging.info("Starting Hydra Observer")

    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
        p = r.pubsub()
        p.subscribe(REDIS_CHANNEL)
        logging.info(f"Subscribed to Redis channel: {REDIS_CHANNEL}")
    except Exception as e:
        logging.error(f"Could not connect to Redis: {e}")
        return

    for message in p.listen():
        if message['type'] == 'message':
            try:
                log_data = json.loads(message['data'])
                logging.info(f"Received log: {log_data}")
                analyze_log(log_data)
            except json.JSONDecodeError:
                logging.error(f"Could not decode message: {message['data']}")
            except Exception as e:
                logging.error(f"Error processing message: {e}")

if __name__ == "__main__":
    main()
