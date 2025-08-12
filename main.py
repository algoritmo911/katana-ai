import os
import uvicorn
import redis.asyncio as redis
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

# --- Environment Variables ---
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_QUEUE_NAME = os.getenv("REDIS_QUEUE_NAME", "katana_task_queue")


# --- Lifespan Management for Redis Connection ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events for the FastAPI application.
    Connects to Redis on startup and disconnects on shutdown.
    """
    print("Connecting to Redis...")
    try:
        redis_pool = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
        app.state.redis = redis.Redis(connection_pool=redis_pool)
        # Check connection
        await app.state.redis.ping()
        print("✅ Redis connection successful.")
        yield
    except redis.ConnectionError as e:
        print(f"❌ Could not connect to Redis: {e}")
        # We might want to exit if Redis is essential, but for now, we'll let it yield
        # and endpoints will fail.
        yield
    finally:
        if hasattr(app.state, 'redis') and app.state.redis:
            print("Closing Redis connection...")
            await app.state.redis.aclose()
            print("Redis connection closed.")


# --- FastAPI App Setup ---
app = FastAPI(
    title="Katana Task Ingestion API",
    description="Accepts tasks via webhook and places them onto a Redis queue for processing.",
    lifespan=lifespan
)


# --- Pydantic Models ---
class N8nWebhookPayload(BaseModel):
    """Defines the expected payload from the n8n webhook."""
    tasks: List[str]


# --- API Endpoints ---
@app.get("/health", status_code=200)
async def health_check(request: Request):
    """
    Simple health check endpoint to verify API and Redis connectivity.
    """
    redis_status = "ok"
    try:
        await request.app.state.redis.ping()
    except Exception:
        redis_status = "error"

    if redis_status == "error":
        raise HTTPException(status_code=503, detail={"api_status": "ok", "redis_status": "error"})

    return {"api_status": "ok", "redis_status": "ok"}


@app.post("/n8n/webhook", status_code=202)
async def receive_n8n_tasks(payload: N8nWebhookPayload, request: Request):
    """
    Webhook endpoint to receive a list of tasks from n8n and push them to a Redis queue.
    """
    if not hasattr(request.app.state, 'redis') or not request.app.state.redis:
         raise HTTPException(status_code=503, detail="Redis connection not available.")

    if not payload.tasks:
        # Still return 202 Accepted, as the request was valid, just empty.
        return {"message": "Received empty task list. No action taken."}

    try:
        # Loop and push tasks one by one.
        # For a small number of tasks, the overhead is negligible.
        # This also simplifies testing as fakeredis doesn't fully support pipelines.
        for task in payload.tasks:
            await request.app.state.redis.rpush(REDIS_QUEUE_NAME, task)

        print(f"Queued {len(payload.tasks)} tasks to Redis list '{REDIS_QUEUE_NAME}'.")
        return {"message": f"Successfully queued {len(payload.tasks)} tasks."}

    except redis.RedisError as e:
        print(f"Error queueing tasks to Redis: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue tasks to Redis.")


# --- Main Execution ---
if __name__ == "__main__":
    print("Starting Katana Task Ingestion API server...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=True # Enable reload for local development
    )
