import logging
import time
from datetime import timedelta
from fastapi import FastAPI, Request, HTTPException
from telegram import Update as TelegramUpdate
from telegram.ext import Application
import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import asyncio  # Added for task queue management

from katana.exchange.coinbase_api import get_spot_price
from katana_bot import KatanaBot
from logging_config import setup_logging

# Task Queue Imports
from katana.task_queue.redis_broker import RedisBroker
from katana.task_queue.service import TaskQueueService
from katana.task_queue.models import (
    Task,
)  # Required for type hint if not using string forward reference fully

# Configure logging
setup_logging(logging.DEBUG)
logger = logging.getLogger(__name__)

# --- Application Setup ---
app = FastAPI(title="KatanaBot API", version="0.1.0")
START_TIME = time.time()

# Initialize KatanaBot (consider how to manage state if multiple worker processes are used)
katana_bot_instance = KatanaBot("WebhookKatanaBot")

# --- Telegram Bot Setup ---
# It's better to get this from environment variables or a config file
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"  # User must replace this
WEBHOOK_URL = (
    "https://your-actual-domain-or-ngrok-url.com/webhook"  # User must replace this
)
REDIS_URL = "redis://localhost:6379/0"  # For Task Queue

telegram_app = None  # Will be initialized on startup
scheduler = None  # Will be initialized on startup
task_broker = None  # Will be initialized on startup


# --- Scheduler Job ---
async def scheduled_task_example():
    """Example of a task that runs periodically."""
    logger.info(
        "Scheduled task executed: Performing self-check or periodic synchronization."
    )
    # In a real application, this could be:
    # - katana_bot_instance.perform_self_check()
    # - katana_bot_instance.synchronize_data()
    # - Logging bot health metrics


# --- FastAPI Event Handlers ---
@app.on_event("startup")
async def startup_event():
    global telegram_app, scheduler

    # 1. Initialize Telegram Application
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        logger.warning(
            "TELEGRAM_BOT_TOKEN is not set. Webhook registration and Telegram functionality will be disabled."
        )
        telegram_app = None
    else:
        telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        # Set webhook
        if (
            not WEBHOOK_URL
            or WEBHOOK_URL == "https://your-actual-domain-or-ngrok-url.com/webhook"
        ):
            logger.warning(
                f"WEBHOOK_URL is not properly set. Telegram webhook will not be registered."
            )
        else:
            try:
                await telegram_app.bot.set_webhook(
                    url=WEBHOOK_URL,
                    allowed_updates=TelegramUpdate.ALL_TYPES,
                    drop_pending_updates=True,
                )
                logger.info(f"Webhook successfully set to {WEBHOOK_URL}")
            except Exception as e:
                logger.error(
                    f"Failed to set webhook to {WEBHOOK_URL}: {e}", exc_info=True
                )
                telegram_app = None  # Disable telegram app if webhook fails

    # 2. Initialize and Start Scheduler
    scheduler = AsyncIOScheduler(timezone="UTC")  # It's good practice to set a timezone

    # Add jobs to the scheduler
    scheduler.add_job(
        scheduled_task_example,
        trigger=IntervalTrigger(seconds=300),  # Example: run every 5 minutes
        id="periodic_self_check",
        name="Periodic Self-Check/Sync",
        replace_existing=True,
    )
    # Add more jobs as needed
    # scheduler.add_job(another_task, "cron", hour=3, minute=0) # Example: daily at 3 AM UTC

    scheduler.start()
    logger.info("APScheduler started with initial jobs.")

    # 3. Initialize Task Queue Service
    global task_queue_service, task_queue_worker_tasks

    # --- Task Queue Executors ---
    async def price_task_executor(task: "Task"):
        """
        Task executor to fetch a spot price and send it back to a Telegram chat.
        """
        chat_id = task.payload.get("chat_id")
        pair = task.payload.get("pair")
        if not chat_id or not pair:
            logger.error(
                f"Task {task.id} is missing 'chat_id' or 'pair' in its payload."
            )
            return  # Or raise an exception to mark the task as failed

        logger.info(f"Executing price task for pair '{pair}' for chat_id {chat_id}")
        price = get_spot_price(pair)  # This is a blocking I/O call
        if price is not None:
            response_message = (
                f"KatanaBot: Current price for {pair}: {price} (currency from pair)"
            )
        else:
            response_message = (
                f"KatanaBot: Could not fetch price for {pair}. See server logs for details."
            )

        if telegram_app:
            try:
                await telegram_app.bot.send_message(
                    chat_id=chat_id, text=response_message
                )
                logger.info(f"Successfully sent price update to chat_id {chat_id}")
            except Exception as e:
                logger.error(
                    f"Failed to send message to chat_id {chat_id}: {e}", exc_info=True
                )
        else:
            logger.warning(
                f"Telegram app not available, cannot send price update for task {task.id}"
            )

    task_executors = {
        "get_price_and_reply": price_task_executor,
    }
    # Initialize broker and service
    # These will be accessible globally for adding tasks from other parts of the app if needed
    # For a larger app, consider dependency injection for these.
    global task_broker
    task_broker = RedisBroker(redis_url=REDIS_URL)
    task_queue_service = TaskQueueService(
        broker=task_broker, task_executors=task_executors
    )

    # Start task queue workers
    num_task_workers = 2  # Configurable
    task_queue_worker_tasks = task_queue_service.start_workers(
        num_workers=num_task_workers, poll_interval=0.5
    )
    logger.info(f"TaskQueueService started with {num_task_workers} worker(s).")


    logger.info("FastAPI application startup sequence complete.")


@app.on_event("shutdown")
async def shutdown_event():
    global scheduler, telegram_app, task_queue_service, task_queue_worker_tasks, task_broker

    # 1. Shutdown Task Queue Service
    if task_queue_service and task_queue_worker_tasks:
        logger.info("Attempting to shut down TaskQueueService workers...")
        await task_queue_service.shutdown()  # Signal workers to stop
        try:
            # Wait for worker tasks to complete with a timeout
            done, pending = await asyncio.wait(task_queue_worker_tasks, timeout=10.0)
            if pending:
                logger.warning(
                    f"{len(pending)} task queue workers did not shut down gracefully within timeout. Forcing cancellation."
                )
                for task in pending:
                    task.cancel()
                # Optionally await again with a very short timeout after cancellation
                await asyncio.wait(pending, timeout=1.0)
            logger.info(
                f"TaskQueueService workers shut down. {len(done)} completed gracefully."
            )
        except asyncio.TimeoutError:
            logger.error(
                "Timeout waiting for task queue workers to shut down. Some tasks might not have finished."
            )
        except Exception as e:
            logger.error(f"Error during TaskQueueService shutdown: {e}", exc_info=True)

    # 2. Close Broker Connection
    if task_broker:
        logger.info("Attempting to close RedisBroker connection...")
        try:
            await task_broker.close()
            logger.info("RedisBroker connection closed.")
        except Exception as e:
            logger.error(f"Error closing RedisBroker connection: {e}", exc_info=True)

    # 3. Shutdown Scheduler
    if scheduler and scheduler.running:
        logger.info("Attempting to shut down APScheduler...")
        scheduler.shutdown(
            wait=True
        )  # Changed to wait=True for cleaner shutdown if possible
        logger.info("APScheduler shut down.")

    # 3. Clean up Telegram (optional webhook deletion)
    if telegram_app and telegram_app.bot:
        # Current decision: do not delete webhook on shutdown by default for most production scenarios.
        # If you need to delete it (e.g. for temporary ngrok URLs or specific cleanup):
        # try:
        #     logger.info(f"Attempting to delete webhook: {WEBHOOK_URL}")
        #     await telegram_app.bot.delete_webhook()
        #     logger.info(f"Webhook {WEBHOOK_URL} deleted successfully.")
        # except Exception as e:
        #     logger.error(f"Error during webhook deletion for {WEBHOOK_URL}: {e}", exc_info=True)
        pass

    logger.info("FastAPI application shutdown sequence complete.")


# --- API Endpoints ---
@app.post("/webhook")
async def telegram_webhook(request: Request):
    if not telegram_app:
        logger.error("Telegram app not initialized. Cannot process webhook.")
        raise HTTPException(
            status_code=503,
            detail="Telegram integration not available. Bot token may not be configured.",
        )

    try:
        data = await request.json()
        tg_update = TelegramUpdate.de_json(data, telegram_app.bot)
        logger.debug(f"Received raw update data: {data}")
        logger.info(f"Processing Telegram update ID: {tg_update.update_id}")

        if tg_update.message and tg_update.message.text:
            command_text = tg_update.message.text
            chat_id = tg_update.message.chat_id

            logger.info(f"Handling command '{command_text}' for chat_id {chat_id}")

            # --- Command Routing ---
            command_parts = command_text.strip().lower().split()
            command = command_parts[0] if command_parts else ""

            # Route to task queue for slow commands, handle fast commands directly
            if command == "!price":
                if len(command_parts) == 2 and task_queue_service:
                    pair = command_parts[1].upper()
                    # Enqueue the task
                    await task_queue_service.add_task(
                        name="get_price_and_reply",
                        payload={"chat_id": chat_id, "pair": pair},
                        priority=2,  # Normal priority
                    )
                    # Send immediate feedback to the user
                    await telegram_app.bot.send_message(
                        chat_id=chat_id,
                        text=f"Request for price of {pair} received. I'm on it!",
                    )
                    return {
                        "status": "ok",
                        "message": f"Task enqueued for !price command for {pair}",
                    }
                else:
                    # Handle incorrect usage of !price command
                    await telegram_app.bot.send_message(
                        chat_id=chat_id,
                        text="Usage: !price <TRADING-PAIR> (e.g., !price BTC-USD)",
                    )
                    return {
                        "status": "error",
                        "message": "Invalid !price command format.",
                    }
            else:
                # Handle other commands synchronously
                response_text = katana_bot_instance.handle_command(command_text)
                if response_text:
                    await telegram_app.bot.send_message(
                        chat_id=chat_id, text=response_text
                    )
                else:
                    # Optional: handle cases where no response is generated
                    await telegram_app.bot.send_message(
                        chat_id=chat_id,
                        text="Command processed, but no specific reply was generated.",
                    )
                return {
                    "status": "ok",
                    "message": "Synchronous command processed and response sent",
                }
        elif tg_update.message:  # Message received but no text (e.g. photo, sticker)
            logger.info(
                f"Received non-text message from chat_id {tg_update.message.chat_id}. Type: {tg_update.message.chat.type if tg_update.message.chat else 'Unknown'}"
            )
            # Optionally handle other message types or inform the user
            await telegram_app.bot.send_message(
                chat_id=tg_update.message.chat_id,
                text="I can currently only process text commands.",
            )
            return {"status": "ok", "message": "Non-text message received"}
        else:
            logger.info(
                f"Received an update that is not a message or has no text: {tg_update}"
            )
            return {
                "status": "ok",
                "message": "Update received but not actionable by current logic",
            }

    except Exception as e:
        logger.error(f"Error processing webhook update: {e}", exc_info=True)
        # Avoid sending detailed error messages back to Telegram for security reasons,
        # but ensure it's logged thoroughly.
        raise HTTPException(
            status_code=500, detail="Internal server error processing update."
        )


@app.get("/health")
async def health_check():
    """Returns a simple health check indicating the API is running."""
    return {"status": "OK", "message": "API is healthy."}


@app.get("/status")
async def get_status():
    """Returns a more detailed status of the application."""
    uptime_seconds = time.time() - START_TIME
    uptime_delta = timedelta(seconds=uptime_seconds)

    scheduler_status = "not_initialized"
    scheduler_running = False
    scheduled_jobs_count = 0
    next_run_times = []

    if scheduler:
        scheduler_running = scheduler.running
        scheduler_status = "running" if scheduler_running else "stopped"
        try:
            jobs = scheduler.get_jobs()
            scheduled_jobs_count = len(jobs)
            for job in jobs:
                next_run_times.append(
                    {
                        "job_id": job.id,
                        "next_run": (
                            job.next_run_time.isoformat()
                            if job.next_run_time
                            else "N/A"
                        ),
                    }
                )
        except Exception as e:
            logger.error(f"Error retrieving scheduler job details: {e}", exc_info=True)
            scheduler_status = "error_retrieving_jobs"

    return {
        "application_status": "running",
        "uptime": str(uptime_delta),
        "version": app.version,
        "telegram_integration": {
            "bot_status": (
                "active_and_webhook_set"
                if telegram_app and telegram_app.bot.token
                else "inactive_or_webhook_failed"
            ),
            "token_configured": bool(
                TELEGRAM_BOT_TOKEN and TELEGRAM_BOT_TOKEN != "YOUR_TELEGRAM_BOT_TOKEN"
            ),
            "webhook_url_configured": bool(
                WEBHOOK_URL
                and WEBHOOK_URL != "https://your-actual-domain-or-ngrok-url.com/webhook"
            ),
            "webhook_url_used": WEBHOOK_URL if telegram_app else "N/A",
        },
        "scheduler": {
            "status": scheduler_status,
            "running": scheduler_running,
            "jobs_count": scheduled_jobs_count,
            "job_next_runs": next_run_times,
        },
        "task_queue_service": {
            "status": "active" if task_queue_service else "inactive",
            "broker_type": (
                task_queue_service.broker.__class__.__name__
                if task_queue_service
                else "N/A"
            ),
            "num_workers": (
                len(task_queue_worker_tasks) if task_queue_worker_tasks else 0
            ),
            "registered_task_names": (
                list(task_queue_service.task_executors.keys())
                if task_queue_service
                else []
            ),
            # Potentially add queue size if broker supports it easily (InMemoryBroker has get_queue_size)
        },
    }


@app.get("/uptime")
async def get_uptime():
    """Returns the application's uptime."""
    uptime_seconds = time.time() - START_TIME
    uptime_delta = timedelta(seconds=uptime_seconds)
    return {"uptime_seconds": uptime_seconds, "uptime_human": str(uptime_delta)}


# --- Debug Endpoint for Task Queue ---
from pydantic import BaseModel
from typing import Dict, Any, Optional


class AddTaskRequest(BaseModel):
    name: str
    payload: Dict[str, Any]
    priority: int = 0
    delay_seconds: Optional[float] = None


@app.post("/debug/add_task", tags=["Debug - Task Queue"])
async def debug_add_task_endpoint(task_request: AddTaskRequest):
    """
    Debug endpoint to manually add a task to the queue.
    Requires task_queue_service to be initialized.
    """
    if not task_queue_service:
        raise HTTPException(status_code=503, detail="TaskQueueService not available.")

    try:
        logger.info(
            f"Debug endpoint: Attempting to add task: {task_request.name} with payload {task_request.payload}"
        )
        task = await task_queue_service.add_task(
            name=task_request.name,
            payload=task_request.payload,
            priority=task_request.priority,
            delay_seconds=task_request.delay_seconds,
        )
        logger.info(
            f"Debug endpoint: Task {task.id} (Name: {task.name}) enqueued successfully."
        )
        return {
            "message": "Task enqueued successfully",
            "task_id": task.id,
            "task_name": task.name,
            "status": task.status.name,
            "scheduled_at": task.scheduled_at.isoformat(),
            "priority": task.priority,
        }
    except ValueError as ve:  # Handles unknown task name
        logger.error(f"Debug endpoint: ValueError adding task - {ve}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Debug endpoint: Error adding task - {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )


if __name__ == "__main__":
    # This is for local development. For production, use a Gunicorn or Uvicorn process manager.
    # The webhook URL for Telegram must be publicly accessible (e.g., using ngrok for local dev).
    logger.info("Starting KatanaBot API with Uvicorn...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
