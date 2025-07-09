import logging
import time
import os # Added for environment variables
from datetime import timedelta
from fastapi import FastAPI, Request, HTTPException
from telegram import Update as TelegramUpdate
from telegram.ext import Application
import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from katana_bot import KatanaBot
from logging_config import setup_logging

# Configure logging
setup_logging(logging.DEBUG)
logger = logging.getLogger(__name__)

# --- Application Setup ---
app = FastAPI(title="KatanaBot API", version="0.1.0")
START_TIME = time.time()

# Initialize KatanaBot (consider how to manage state if multiple worker processes are used)
katana_bot_instance = KatanaBot("WebhookKatanaBot")

# --- Telegram Bot Setup ---
# Load from environment variables provided by Doppler
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

telegram_app = None # Will be initialized on startup
scheduler = None    # Will be initialized on startup

# --- Scheduler Job ---
async def scheduled_task_example():
    """Example of a task that runs periodically."""
    logger.info("Scheduled task executed: Performing self-check or periodic synchronization.")
    # In a real application, this could be:
    # - katana_bot_instance.perform_self_check()
    # - katana_bot_instance.synchronize_data()
    # - Logging bot health metrics

# --- FastAPI Event Handlers ---
@app.on_event("startup")
async def startup_event():
    global telegram_app, scheduler

    # 1. Initialize Telegram Application
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN environment variable is not set. Webhook registration and Telegram functionality will be disabled.")
        telegram_app = None
    else:
        telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        # Set webhook
        if not WEBHOOK_URL:
            logger.warning(f"WEBHOOK_URL environment variable is not properly set. Telegram webhook will not be registered.")
        else:
            try:
                await telegram_app.bot.set_webhook(
                    url=WEBHOOK_URL,
                    allowed_updates=TelegramUpdate.ALL_TYPES,
                    drop_pending_updates=True
                )
                logger.info(f"Webhook successfully set to {WEBHOOK_URL}")
            except Exception as e:
                logger.error(f"Failed to set webhook to {WEBHOOK_URL}: {e}", exc_info=True)
                telegram_app = None # Disable telegram app if webhook fails

    # 2. Initialize and Start Scheduler
    scheduler = AsyncIOScheduler(timezone="UTC") # It's good practice to set a timezone

    # Add jobs to the scheduler
    scheduler.add_job(
        scheduled_task_example,
        trigger=IntervalTrigger(seconds=300), # Example: run every 5 minutes
        id="periodic_self_check",
        name="Periodic Self-Check/Sync",
        replace_existing=True
    )
    # Add more jobs as needed
    # scheduler.add_job(another_task, "cron", hour=3, minute=0) # Example: daily at 3 AM UTC

    scheduler.start()
    logger.info("APScheduler started with initial jobs.")

    logger.info("FastAPI application startup sequence complete.")

@app.on_event("shutdown")
async def shutdown_event():
    global scheduler, telegram_app

    # 1. Shutdown Scheduler
    if scheduler and scheduler.running:
        logger.info("Attempting to shut down APScheduler...")
        scheduler.shutdown(wait=False) # wait=False for async context, or True if issues arise
        logger.info("APScheduler shut down.")

    # 2. Clean up Telegram (optional webhook deletion)
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
        raise HTTPException(status_code=503, detail="Telegram integration not available. Bot token may not be configured.")

    try:
        data = await request.json()
        tg_update = TelegramUpdate.de_json(data, telegram_app.bot)
        logger.debug(f"Received raw update data: {data}")
        logger.info(f"Processing Telegram update ID: {tg_update.update_id}")

        if tg_update.message and tg_update.message.text:
            command_text = tg_update.message.text
            chat_id = tg_update.message.chat_id

            logger.info(f"Handling command '{command_text}' for chat_id {chat_id}")

            # Call KatanaBot's handle_command, which now returns a response string
            response_text = katana_bot_instance.handle_command(command_text)

            if response_text:
                logger.info(f"Sending response to chat_id {chat_id}: {response_text}")
                await telegram_app.bot.send_message(chat_id=chat_id, text=response_text)
            else:
                logger.warning(f"No response generated by handle_command for input: {command_text}")
                # Optionally send a default acknowledgement or error message
                await telegram_app.bot.send_message(chat_id=chat_id, text="Command processed, but no specific reply was generated.")

            return {"status": "ok", "message": "Command processed and response sent"}
        elif tg_update.message: # Message received but no text (e.g. photo, sticker)
            logger.info(f"Received non-text message from chat_id {tg_update.message.chat_id}. Type: {tg_update.message.chat.type if tg_update.message.chat else 'Unknown'}")
            # Optionally handle other message types or inform the user
            await telegram_app.bot.send_message(chat_id=tg_update.message.chat_id, text="I can currently only process text commands.")
            return {"status": "ok", "message": "Non-text message received"}
        else:
            logger.info(f"Received an update that is not a message or has no text: {tg_update}")
            return {"status": "ok", "message": "Update received but not actionable by current logic"}

    except Exception as e:
        logger.error(f"Error processing webhook update: {e}", exc_info=True)
        # Avoid sending detailed error messages back to Telegram for security reasons,
        # but ensure it's logged thoroughly.
        raise HTTPException(status_code=500, detail="Internal server error processing update.")

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
                next_run_times.append({
                    "job_id": job.id,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else "N/A"
                })
        except Exception as e:
            logger.error(f"Error retrieving scheduler job details: {e}", exc_info=True)
            scheduler_status = "error_retrieving_jobs"

    return {
        "application_status": "running",
        "uptime": str(uptime_delta),
        "version": app.version,
        "telegram_integration": {
            "bot_status": "active_and_webhook_set" if telegram_app and telegram_app.bot.token else "inactive_or_webhook_failed",
            "token_configured": bool(TELEGRAM_BOT_TOKEN),
            "webhook_url_configured": bool(WEBHOOK_URL),
            "webhook_url_used": WEBHOOK_URL if telegram_app else "N/A"
        },
        "scheduler": {
            "status": scheduler_status,
            "running": scheduler_running,
            "jobs_count": scheduled_jobs_count,
            "job_next_runs": next_run_times
        }
    }

@app.get("/uptime")
async def get_uptime():
    """Returns the application's uptime."""
    uptime_seconds = time.time() - START_TIME
    uptime_delta = timedelta(seconds=uptime_seconds)
    return {"uptime_seconds": uptime_seconds, "uptime_human": str(uptime_delta)}

if __name__ == "__main__":
    # This is for local development. For production, use a Gunicorn or Uvicorn process manager.
    # The webhook URL for Telegram must be publicly accessible (e.g., using ngrok for local dev).
    logger.info("Starting KatanaBot API with Uvicorn...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
