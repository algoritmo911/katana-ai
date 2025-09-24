import asyncio
import json
import os
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from src.orchestrator.task_orchestrator import TaskOrchestrator
from src.agents.julius_agent import JuliusAgent

TASKS_FILE = "tasks.json"
ROUND_INTERVAL_SECONDS = 30
ORCHESTRATOR_LOG_FILE = "orchestrator_log.json" # Centralize log file name

# --- FastAPI App Setup ---
app = FastAPI(title="Julius Task Orchestrator API")

# This will be populated when the main application starts
# Not ideal for global state, but simple for this example.
# A better approach for larger apps might involve dependency injection or app state.
orchestrator_instance: TaskOrchestrator = None


class NewTaskPayload(BaseModel):
    task: str

@app.post("/n8n/new-task", response_model=Dict[str, str])
async def receive_new_task(payload: NewTaskPayload):
    """
    Receives a new task from an n8n webhook and adds it to the orchestrator's queue.
    """
    if orchestrator_instance is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    if not payload.task:
        raise HTTPException(status_code=400, detail="Task cannot be empty")

    orchestrator_instance.add_tasks([payload.task])
    print(f"Received new task from n8n: {payload.task}")
    return {"status": "Task added successfully"}


@app.get("/orchestrator/status", response_model=Dict[str, Any])
async def get_orchestrator_status():
    """
    Provides the current status of the TaskOrchestrator,
    including current batch size, task queue length, and metrics for the last 10 rounds.
    """
    if orchestrator_instance is None:
        return {"error": "Orchestrator not initialized"}
    return orchestrator_instance.get_status()

# --- Task Loading ---
def load_tasks_from_json(file_path: str) -> list[str]:
    """Loads a list of tasks from a JSON file."""
    if not os.path.exists(file_path):
        print(f"Warning: Tasks file not found at {file_path}. Starting with an empty task queue.")
        return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list) and all(isinstance(item, str) for item in data):
                return data
            else:
                print(f"Warning: Tasks file {file_path} does not contain a list of strings. Starting with an empty task queue.")
                return []
    except json.JSONDecodeError:
        print(f"Warning: Error decoding JSON from {file_path}. Starting with an empty task queue.")
        return []
    except Exception as e:
        print(f"Warning: An unexpected error occurred while loading tasks: {e}. Starting with an empty task queue.")
        return []

# --- Orchestrator Loop ---
async def run_orchestrator_loop(orchestrator: TaskOrchestrator):
    """The main loop for the task orchestrator."""
    global orchestrator_instance
    orchestrator_instance = orchestrator # Make instance available to FastAPI endpoint

    print("Initializing Julius Task Orchestration System...")
    # 3. Load initial tasks
    initial_tasks = load_tasks_from_json(TASKS_FILE)
    if initial_tasks:
        orchestrator.add_tasks(initial_tasks)
        print(f"Loaded {len(initial_tasks)} tasks into the orchestrator.")
    else:
        print("No initial tasks loaded. Add tasks to tasks.json or use an API if available.")

    try:
        round_number = 1
        while True:
            if not orchestrator.task_queue:
                print(f"No tasks in queue. Waiting for {ROUND_INTERVAL_SECONDS} seconds or new tasks...")
                await asyncio.sleep(ROUND_INTERVAL_SECONDS)
                continue

            print(f"\n--- Starting Orchestrator Round {round_number} ---")
            await orchestrator.run_round()
            print(f"--- Finished Orchestrator Round {round_number} ---")

            round_number += 1
            print(f"Waiting {ROUND_INTERVAL_SECONDS} seconds for the next round...")
            await asyncio.sleep(ROUND_INTERVAL_SECONDS)

    except asyncio.CancelledError:
        print("\nOrchestrator loop cancelled.")
    except KeyboardInterrupt: # Should be caught by main, but good to have robustness
        print("\nOrchestrator loop interrupted by KeyboardInterrupt.")
    finally:
        print("Orchestrator loop stopped.")


# --- Main Application Setup ---
async def main_async_app():
    # 1. Initialize Agent
    julius_agent = JuliusAgent()

    # 2. Initialize TaskOrchestrator
    # Pass the log file name defined globally
    local_orchestrator = TaskOrchestrator(
        agent=julius_agent,
        batch_size=3,
        max_batch=10,
        metrics_log_file=ORCHESTRATOR_LOG_FILE
    )

    # Configure Uvicorn server
    # Note: Uvicorn's `run` is blocking, so we use `Server.serve()` for async context
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)

    # Run orchestrator loop and FastAPI server concurrently
    orchestrator_task = asyncio.create_task(run_orchestrator_loop(local_orchestrator))
    fastapi_task = asyncio.create_task(server.serve())

    print("FastAPI server starting on http://0.0.0.0:8000")
    print("Orchestrator starting its loop.")

    try:
        # await orchestrator_task # If we await only one, the other might not shutdown gracefully on KeyboardInterrupt
        # await fastapi_task
        done, pending = await asyncio.wait(
            [orchestrator_task, fastapi_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True) # Ensure cancellations are processed

    except KeyboardInterrupt:
        print("\nShutting down application (main_async_app)...")
        # Cancel tasks explicitly on KeyboardInterrupt
        orchestrator_task.cancel()
        fastapi_task.cancel() # Uvicorn server might need more graceful shutdown
        await asyncio.gather(orchestrator_task, fastapi_task, return_exceptions=True)
    finally:
        print("Application shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main_async_app())
