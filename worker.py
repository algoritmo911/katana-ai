import asyncio
import os
import redis.asyncio as redis
import logging

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("KatanaWorker")

# --- Environment Variables ---
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_QUEUE_NAME = os.getenv("REDIS_QUEUE_NAME", "katana_task_queue")
WORKER_RECONNECT_DELAY = 5  # seconds

async def execute_task(task: str):
    """
    Simulates the execution of a task.
    For now, it just logs the content of the task.
    """
    logger.info(f"Executing task: {task}")
    # In the future, this is where the actual task processing logic would go.
    # For example, calling an agent, processing data, etc.
    await asyncio.sleep(1) # Simulate I/O bound work
    logger.info(f"✅ Task completed: {task}")

async def main(shutdown_event: asyncio.Event = None):
    """
    The main worker loop. Connects to Redis and processes tasks from the queue.
    The loop can be gracefully shut down by setting the `shutdown_event`.
    """
    logger.info("Starting Katana Worker...")

    while not shutdown_event or not shutdown_event.is_set():
        try:
            # Connect to Redis
            r = await redis.from_url(
                f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
                decode_responses=True
            )
            await r.ping()
            logger.info(f"Successfully connected to Redis. Listening on queue '{REDIS_QUEUE_NAME}'...")

            # Main processing loop
            while not shutdown_event or not shutdown_event.is_set():
                try:
                    # BLPOP with a timeout to allow checking the shutdown_event periodically.
                    task_data = await r.blpop(REDIS_QUEUE_NAME, timeout=1)

                    if task_data:
                        queue, task_content = task_data
                        logger.info(f"Pulled task from queue '{queue}': {task_content}")
                        await execute_task(task_content)
                    # If task_data is None, the loop continues and checks the shutdown_event.

                except redis.ConnectionError as e:
                    logger.error(f"Redis connection lost: {e}. Attempting to reconnect...")
                    break # Break inner loop to trigger reconnection
                except Exception as e:
                    logger.error(f"An unexpected error occurred during task processing: {e}", exc_info=True)
                    await asyncio.sleep(WORKER_RECONNECT_DELAY)

        except redis.ConnectionError as e:
            if not shutdown_event or not shutdown_event.is_set():
                logger.error(f"Could not connect to Redis: {e}. Retrying in {WORKER_RECONNECT_DELAY} seconds...")
                await asyncio.sleep(WORKER_RECONNECT_DELAY)
        except KeyboardInterrupt:
            logger.info("Worker shutting down by user request.")
            break
        finally:
            if 'r' in locals() and r:
                await r.aclose()

    logger.info("Katana Worker has stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Main process caught KeyboardInterrupt.")
