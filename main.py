import asyncio
import json
import os
from typing import Dict, Any
from dotenv import load_dotenv

from fastapi import FastAPI
import uvicorn

from src.orchestrator.task_orchestrator import TaskOrchestrator
from src.agents.julius_agent import JuliusAgent

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
ROUND_INTERVAL_SECONDS = 5 # Check for new tasks more frequently
ORCHESTRATOR_LOG_FILE = "orchestrator_log.json"
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_DB = int(os.getenv('REDIS_DB', '0'))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
TASK_QUEUE_NAME = os.getenv('REDIS_TASK_QUEUE_NAME', 'katana:task_queue')


# --- FastAPI App Setup ---
app = FastAPI(title="Katana Task Orchestrator API")

# This will be populated when the main application starts
orchestrator_instance: TaskOrchestrator = None


@app.get("/orchestrator/status", response_model=Dict[str, Any])
async def get_orchestrator_status():
    """
    Provides the current status of the TaskOrchestrator,
    including current batch size, task queue length from Redis, and metrics for the last 10 rounds.
    """
    if orchestrator_instance is None:
        return {"error": "Orchestrator not initialized"}
    return orchestrator_instance.get_status()

# --- Orchestrator Loop ---
async def run_orchestrator_loop(orchestrator: TaskOrchestrator):
    """The main loop for the task orchestrator."""
    global orchestrator_instance
    orchestrator_instance = orchestrator # Make instance available to FastAPI endpoint

    print("Initializing Julius Task Orchestration System...")
    # No longer loading tasks from JSON file. Orchestrator will pull from Redis.
    print(f"Orchestrator is now monitoring Redis queue '{TASK_QUEUE_NAME}' for tasks.")

    try:
        round_number = 1
        while True:
            # The run_round method now handles the empty queue case internally.
            # We can just call it in a loop.
            # print(f"\n--- Starting Orchestrator Round {round_number} ---") # Too noisy
            await orchestrator.run_round()
            # print(f"--- Finished Orchestrator Round {round_number} ---") # Too noisy

            round_number += 1
            # Wait for the next round.
            await asyncio.sleep(ROUND_INTERVAL_SECONDS)

    except asyncio.CancelledError:
        print("\nOrchestrator loop cancelled.")
    except KeyboardInterrupt:
        print("\nOrchestrator loop interrupted by KeyboardInterrupt.")
    finally:
        print("Orchestrator loop stopped.")


# --- Main Application Setup ---
async def main_async_app():
    # 1. Initialize Agent
    julius_agent = JuliusAgent()

    # 2. Initialize TaskOrchestrator with Redis configuration
    try:
        local_orchestrator = TaskOrchestrator(
            agent=julius_agent,
            redis_host=REDIS_HOST,
            redis_port=REDIS_PORT,
            redis_db=REDIS_DB,
            redis_password=REDIS_PASSWORD,
            task_queue_name=TASK_QUEUE_NAME,
            metrics_log_file=ORCHESTRATOR_LOG_FILE
        )
    except Exception as e:
        print(f"❌ Failed to initialize TaskOrchestrator. Please check your Redis connection and settings. Error: {e}")
        return # Exit if orchestrator can't be created

    # Configure Uvicorn server
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)

    # Run orchestrator loop and FastAPI server concurrently
    orchestrator_task = asyncio.create_task(run_orchestrator_loop(local_orchestrator))
    fastapi_task = asyncio.create_task(server.serve())

    print("FastAPI server starting on http://0.0.0.0:8000")
    print(f"Orchestrator loop starting, checking for tasks every {ROUND_INTERVAL_SECONDS} seconds.")

    try:
        done, pending = await asyncio.wait(
            [orchestrator_task, fastapi_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)

    except KeyboardInterrupt:
        print("\nShutting down application (main_async_app)...")
        orchestrator_task.cancel()
        # Uvicorn's server.serve() doesn't always exit gracefully on task cancellation alone.
        # Calling server.shutdown() is more explicit if available, but cancellation is the asyncio way.
        server.should_exit = True
        fastapi_task.cancel()
        await asyncio.gather(orchestrator_task, fastapi_task, return_exceptions=True)
    finally:
        print("Application shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main_async_app())
