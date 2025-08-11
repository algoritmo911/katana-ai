import asyncio
import os
from typing import Dict, Any

from fastapi import FastAPI
import uvicorn

# --- Core Katana Components ---
from src.orchestrator.task_orchestrator import TaskOrchestrator, KatanaTaskProcessor
from src.dao.dao_task_handler import fetch_tasks_from_colony
from src.prometheus.self_healer import analyze_logs_and_generate_tasks
from src.memory.memory_manager import MemoryManager

# --- Configuration ---
ROUND_INTERVAL_SECONDS = 15
ORCHESTRATOR_LOG_FILE = "orchestrator_log.json"

# --- Global Instances (for simplicity in this example) ---
# In a larger app, use dependency injection or app state.
orchestrator_instance: TaskOrchestrator = None
memory_manager_instance: MemoryManager = None

# --- FastAPI App Setup ---
app = FastAPI(title="Katana Autonomous Engine API")

@app.get("/status", response_model=Dict[str, Any])
async def get_orchestrator_status():
    """
    Provides the current status of the TaskOrchestrator,
    including current batch size, task queue length, and metrics for the last 10 rounds.
    """
    if orchestrator_instance is None:
        return {"error": "Orchestrator not initialized"}
    return orchestrator_instance.get_status()

# --- Main Autonomous Loop ---
async def run_autonomous_loop(orchestrator: TaskOrchestrator, memory: MemoryManager):
    """The main autonomous loop for the Katana engine."""
    global orchestrator_instance, memory_manager_instance
    orchestrator_instance = orchestrator
    memory_manager_instance = memory

    print("Initializing Katana Autonomous Engine...")

    # Example chat_id for DAO to pull context from. In a real multi-user
    # system, this would be managed dynamically.
    EXAMPLE_CHAT_ID = "user_main_session"

    try:
        round_number = 1
        while True:
            print(f"\n--- Starting Katana Autonomous Round {round_number} ---")

            # 1. Observe (Prometheus): Analyze performance and generate self-healing tasks.
            print("[Loop] Analyzing logs for self-healing opportunities...")
            healing_tasks = analyze_logs_and_generate_tasks(ORCHESTRATOR_LOG_FILE)
            if healing_tasks:
                print(f"[Loop] Prometheus generated {len(healing_tasks)} healing task(s).")
                orchestrator.add_tasks(healing_tasks)

            # 2. Orient (DAO): Generate tasks based on goals, knowledge, and memory.
            print("[Loop] Consulting DAO for new tasks...")
            # Pass memory manager and chat_id to get context-aware tasks.
            dao_tasks = fetch_tasks_from_colony(memory_manager=memory, chat_id=EXAMPLE_CHAT_ID)
            if dao_tasks:
                print(f"[Loop] DAO generated {len(dao_tasks)} task(s).")
                orchestrator.add_tasks(dao_tasks)

            # 3. Act (Orchestrator): Execute a round of tasks if the queue is not empty.
            if orchestrator.task_queue:
                print(f"[Loop] Task queue has {len(orchestrator.task_queue)} task(s). Running orchestrator round.")
                await orchestrator.run_round()
            else:
                print("[Loop] Task queue is empty. No action taken this round.")

            print(f"--- Finished Katana Autonomous Round {round_number} ---")
            round_number += 1
            print(f"Waiting {ROUND_INTERVAL_SECONDS} seconds for the next round...")
            await asyncio.sleep(ROUND_INTERVAL_SECONDS)

    except asyncio.CancelledError:
        print("\nAutonomous loop cancelled.")
    finally:
        print("Autonomous loop stopped.")


# --- Main Application Setup ---
async def main_async_app():
    # 1. Initialize Core Components
    print("Instantiating Katana components...")
    task_processor = KatanaTaskProcessor()

    # Initialize MemoryManager (requires Redis to be running)
    try:
        memory = MemoryManager()
        if not memory.redis_client:
            print("CRITICAL: Could not connect to Redis. Memory-related functions will fail.")
    except Exception as e:
        print(f"CRITICAL: Failed to initialize MemoryManager: {e}. Exiting.")
        return

    local_orchestrator = TaskOrchestrator(
        agent=task_processor,
        batch_size=3,
        max_batch=10,
        metrics_log_file=ORCHESTRATOR_LOG_FILE
    )

    # 2. Configure Uvicorn server for the API
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)

    # 3. Run autonomous loop and FastAPI server concurrently
    loop_task = asyncio.create_task(run_autonomous_loop(local_orchestrator, memory))
    server_task = asyncio.create_task(server.serve())

    print("Katana Engine starting...")
    print("API server running on http://0.0.0.0:8000/status")

    try:
        done, pending = await asyncio.wait(
            [loop_task, server_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
    except KeyboardInterrupt:
        print("\nShutting down application...")
        loop_task.cancel()
        server_task.cancel()
        await asyncio.gather(loop_task, server_task, return_exceptions=True)
    finally:
        print("Application shutdown complete.")

if __name__ == "__main__":
    # To run this, you need redis-server running in the background.
    # You also need to have run `pip install -r requirements.txt` which should include
    # fastapi, uvicorn, and redis.
    # Note: If requirements.txt is missing these, they need to be added.
    # For now, we assume they are present.
    asyncio.run(main_async_app())
