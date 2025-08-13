import asyncio
import os
import json
from contextlib import asynccontextmanager
from typing import Dict, Any, List

from fastapi import FastAPI, HTTPException
from starlette.requests import Request

# Katana-specific imports
from .exceptions import KatanaAPIException, katana_api_exception_handler, http_exception_handler, generic_exception_handler
from src.agents.julius_agent import JuliusAgent
from src.agents.sync_agent import SyncAgent
from src.memory.memory import Memory
from src.orchestrator.task_orchestrator import TaskOrchestrator

# --- Constants ---
TASKS_FILE = "tasks.json"
ORCHESTRATOR_LOG_FILE = "orchestrator_log.json"
ROUND_INTERVAL_SECONDS = 30
REMOTE_MEMORY_PATH = os.getenv("REMOTE_MEMORY_PATH", "remote:katana/memory")

# --- Helper Functions ---
def load_tasks_from_json(file_path: str) -> list[str]:
    """Loads a list of tasks from a JSON file."""
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, list) and all(isinstance(item, str) for item in data) else []
    except (json.JSONDecodeError, Exception):
        return []

# --- Orchestrator Loop ---
async def run_orchestrator_loop(orchestrator: TaskOrchestrator):
    """The main loop for the task orchestrator."""
    print("Initializing Julius Task Orchestration System...")
    initial_tasks = load_tasks_from_json(TASKS_FILE)
    if initial_tasks:
        orchestrator.add_tasks(initial_tasks)
        print(f"Loaded {len(initial_tasks)} tasks into the orchestrator.")
    else:
        print("No initial tasks loaded.")

    try:
        round_number = 1
        while True:
            if not orchestrator.task_queue:
                await asyncio.sleep(ROUND_INTERVAL_SECONDS)
                continue

            print(f"--- Starting Orchestrator Round {round_number} ---")
            await orchestrator.run_round()
            print(f"--- Finished Orchestrator Round {round_number} ---")
            round_number += 1
            await asyncio.sleep(ROUND_INTERVAL_SECONDS)

    except asyncio.CancelledError:
        print("Orchestrator loop cancelled.")

# --- FastAPI Lifespan Management ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the startup and shutdown of the TaskOrchestrator.
    """
    print("API starting up...")
    # Initialize components
    julius_agent = JuliusAgent()
    memory = Memory()
    sync_agent = SyncAgent(remote_path=REMOTE_MEMORY_PATH)

    orchestrator = TaskOrchestrator(
        agent=julius_agent,
        memory=memory,
        sync_agent=sync_agent,
        batch_size=3,
        max_batch=10,
        metrics_log_file=ORCHESTRATOR_LOG_FILE
    )

    # Store orchestrator in app state to be accessible by endpoints
    app.state.orchestrator = orchestrator

    # Start the orchestrator loop in the background
    orchestrator_task = asyncio.create_task(run_orchestrator_loop(orchestrator))
    print("Orchestrator started in the background.")

    yield

    print("API shutting down...")
    orchestrator_task.cancel()
    try:
        await orchestrator_task
    except asyncio.CancelledError:
        print("Orchestrator task successfully cancelled.")
    print("Shutdown complete.")

# --- FastAPI App Creation ---
app = FastAPI(
    title="Katana API",
    description="The symbiotic nervous system for AI orchestration.",
    version="1.0.0",
    lifespan=lifespan
)

# --- Exception Handlers Registration ---
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(KatanaAPIException, katana_api_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Import and include the API router
from .api import router as api_router
app.include_router(api_router)

@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Katana API is running."}

# In the next steps, we will add the real endpoints, error handlers, etc.
# For now, this sets up the basic application structure.
# To run this app: uvicorn katana_api.main:app --reload
