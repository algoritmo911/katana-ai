import logging
import time
import uuid
from datetime import timedelta
from fastapi import FastAPI, Request, HTTPException
from telegram import Update as TelegramUpdate
from telegram.ext import Application
import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import asyncio

from katana_bot import KatanaBot
from logging_config import setup_logging

# Task Queue Imports
from katana.task_queue.redis_broker import RedisBroker
from katana.task_queue.service import TaskQueueService
from katana.task_queue.models import Task, TaskStatus

# --- Pre-defined tasks for security ---
def example_task_function(x, y):
    """A simple example function that can be called as a task."""
    logger.info(f"Executing example_task_function with args: {x}, {y}")
    return x + y

def send_email(to: str, subject: str, body: str):
    """A mock function to simulate sending an email."""
    logger.info(f"Sending email to {to} with subject '{subject}'")
    logger.info(f"Body: {body}")
    return {"status": "success", "to": to}

async def long_running_process(duration: int):
    """A mock function to simulate a long-running process."""
    logger.info(f"Starting long running process for {duration} seconds.")
    await asyncio.sleep(duration)
    logger.info("Long running process finished.")
    return {"status": "complete", "duration": duration}

# A registry of functions that are allowed to be executed via the API
ALLOWED_TASKS = {
    "example_task": example_task_function,
    "send_email": send_email,
    "long_running_process": long_running_process,
}


# Configure logging
setup_logging(logging.DEBUG)
logger = logging.getLogger(__name__)

# --- Application Setup ---
app = FastAPI(title="KatanaBot API", version="0.1.0")
START_TIME = time.time()

# Initialize KatanaBot
katana_bot_instance = KatanaBot("WebhookKatanaBot")

# --- Telegram Bot Setup ---
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
WEBHOOK_URL = "https://your-actual-domain-or-ngrok-url.com/webhook"
REDIS_URL = "redis://localhost:6379/0"

telegram_app = None
scheduler = None
task_broker = None
task_queue_service = None
task_queue_worker_tasks = []


# --- Scheduler Job ---
async def scheduled_task_example():
    """Example of a task that runs periodically."""
    logger.info("Scheduled task executed: Performing self-check or periodic synchronization.")


# --- FastAPI Event Handlers ---
@app.on_event("startup")
async def startup_event():
    global telegram_app, scheduler, task_queue_service, task_queue_worker_tasks, task_broker

    # 1. Initialize Telegram Application
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        logger.warning("TELEGRAM_BOT_TOKEN is not set. Webhook registration will be disabled.")
    else:
        telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        if not WEBHOOK_URL or WEBHOOK_URL == "https://your-actual-domain-or-ngrok-url.com/webhook":
            logger.warning("WEBHOOK_URL is not properly set. Telegram webhook will not be registered.")
        else:
            try:
                await telegram_app.bot.set_webhook(
                    url=WEBHOOK_URL,
                    allowed_updates=TelegramUpdate.ALL_TYPES,
                    drop_pending_updates=True,
                )
                logger.info(f"Webhook successfully set to {WEBHOOK_URL}")
            except Exception as e:
                logger.error(f"Failed to set webhook to {WEBHOOK_URL}: {e}", exc_info=True)
                telegram_app = None

    # 2. Initialize and Start Scheduler
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        scheduled_task_example,
        trigger=IntervalTrigger(seconds=300),
        id="periodic_self_check",
        name="Periodic Self-Check/Sync",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("APScheduler started.")

    # 3. Initialize Task Queue Service
    task_broker = RedisBroker(redis_url=REDIS_URL)
    task_queue_service = TaskQueueService(broker=task_broker, task_executors={})
    num_task_workers = 2
    task_queue_worker_tasks = task_queue_service.start_workers(
        num_workers=num_task_workers, poll_interval=0.5
    )
    logger.info(f"TaskQueueService started with {num_task_workers} worker(s).")

    logger.info("FastAPI application startup sequence complete.")


@app.on_event("shutdown")
async def shutdown_event():
    global scheduler, telegram_app, task_queue_service, task_queue_worker_tasks, task_broker

    if task_queue_service and task_queue_worker_tasks:
        logger.info("Shutting down TaskQueueService workers...")
        await task_queue_service.shutdown()
        try:
            await asyncio.wait(task_queue_worker_tasks, timeout=10.0)
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for task queue workers to shut down.")

    if task_broker:
        logger.info("Closing RedisBroker connection...")
        await task_broker.close()

    if scheduler and scheduler.running:
        logger.info("Shutting down APScheduler...")
        scheduler.shutdown(wait=True)

    logger.info("FastAPI application shutdown sequence complete.")


# --- API Endpoints ---
@app.post("/webhook")
async def telegram_webhook(request: Request):
    if not telegram_app:
        raise HTTPException(status_code=503, detail="Telegram integration not available.")

    try:
        data = await request.json()
        tg_update = TelegramUpdate.de_json(data, telegram_app.bot)

        if tg_update.message and tg_update.message.text:
            command_text = tg_update.message.text
            chat_id = tg_update.message.chat_id
            response_text = katana_bot_instance.handle_command(command_text)
            if response_text:
                await telegram_app.bot.send_message(chat_id=chat_id, text=response_text)
            return {"status": "ok"}

        return {"status": "ok", "message": "Non-text message received"}
    except Exception as e:
        logger.error(f"Error processing webhook update: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")


@app.get("/health")
async def health_check():
    return {"status": "OK", "message": "API is healthy."}


@app.get("/status")
async def get_status():
    uptime_seconds = time.time() - START_TIME
    uptime_delta = timedelta(seconds=uptime_seconds)
    return {
        "application_status": "running",
        "uptime": str(uptime_delta),
        "version": app.version,
        "telegram_integration": {
            "bot_status": "active" if telegram_app else "inactive",
        },
        "scheduler": {
            "status": "running" if scheduler and scheduler.running else "stopped",
        },
        "task_queue_service": {
            "status": "active" if task_queue_service else "inactive",
            "broker_type": task_broker.__class__.__name__ if task_broker else "N/A",
            "num_workers": len(task_queue_worker_tasks),
        },
    }

# --- Task Queue API Endpoints ---
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

class AddTaskRequest(BaseModel):
    task_name: str
    args: Optional[List[Any]] = []
    kwargs: Optional[Dict[str, Any]] = {}

@app.post("/task", status_code=202)
async def add_task_endpoint(task_request: AddTaskRequest):
    """
    Adds a task to the queue for background processing.
    """
    if not task_queue_service:
        raise HTTPException(status_code=503, detail="TaskQueueService not available.")

    task_function = ALLOWED_TASKS.get(task_request.task_name)
    if not task_function:
        raise HTTPException(status_code=400, detail=f"Task '{task_request.task_name}' not found or not allowed.")

    try:
        task = await task_queue_service.add_task_to_queue(
            task_function, *task_request.args, **task_request.kwargs
        )
        return {
            "message": "Task accepted",
            "task_id": task.id,
            "task_name": task_request.task_name,
            "status_url": f"/task/{task.id}"
        }
    except Exception as e:
        logger.error(f"Error adding task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to enqueue task.")


@app.get("/task/{task_id}")
async def get_task_status_endpoint(task_id: uuid.UUID):
    """
    Retrieves the status of a background task.
    """
    if not task_queue_service:
        raise HTTPException(status_code=503, detail="TaskQueueService not available.")

    status = await task_queue_service.get_task_status(task_id)

    if status is None:
        raise HTTPException(status_code=404, detail="Task not found.")

    return {"task_id": task_id, "status": status.name}


if __name__ == "__main__":
    logger.info("Starting KatanaBot API with Uvicorn...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
