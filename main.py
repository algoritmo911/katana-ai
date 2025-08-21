import logging
import time
from datetime import timedelta
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from telegram import Update as TelegramUpdate
from telegram.ext import Application
import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from katana_bot import KatanaBot
from katana.logging_config import setup_logging
from katana.memory.core import MemoryCore
from katana.oracle import Oracle

# Configure logging
setup_logging(level="DEBUG")
logger = logging.getLogger(__name__)

# --- Application Setup ---
app = FastAPI(title="KatanaBot API", version="0.2.0", description="API for KatanaBot and the Ouranos Protocol Oracle")
START_TIME = time.time()

# --- Core Service Initialization ---
# Initialize MemoryCore, which is the heart of the bot's memory systems.
memory_core = MemoryCore()

# Initialize the main bot instance, passing the memory core to it.
katana_bot_instance = KatanaBot("WebhookKatanaBot", memory=memory_core)

# Initialize the Oracle, the entry point for the agent swarm.
oracle_instance = Oracle(memory=memory_core)


# --- Telegram Bot Setup ---
# It's better to get this from environment variables or a config file
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN" # User must replace this
WEBHOOK_URL = "https://your-actual-domain-or-ngrok-url.com/webhook" # User must replace this

telegram_app = None # Will be initialized on startup
scheduler = None    # Will be initialized on startup

# --- Pydantic Models ---
class OracleQuery(BaseModel):
    question: str
    user_id: str = "api_user" # Default user_id for API calls

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
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        logger.warning("TELEGRAM_BOT_TOKEN is not set. Webhook registration and Telegram functionality will be disabled.")
        telegram_app = None
    else:
        telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        # Set webhook
        if not WEBHOOK_URL or WEBHOOK_URL == "https://your-actual-domain-or-ngrok-url.com/webhook":
            logger.warning(f"WEBHOOK_URL is not properly set. Telegram webhook will not be registered.")
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
    scheduler.start()
    logger.info("APScheduler started with initial jobs.")

    logger.info("FastAPI application startup sequence complete.")

@app.on_event("shutdown")
async def shutdown_event():
    global scheduler, telegram_app

    # 1. Shutdown Scheduler
    if scheduler and scheduler.running:
        logger.info("Attempting to shut down APScheduler...")
        scheduler.shutdown(wait=False)
        logger.info("APScheduler shut down.")

    # 2. Clean up Telegram (optional webhook deletion)
    if telegram_app and telegram_app.bot:
        pass

    logger.info("FastAPI application shutdown sequence complete.")

# --- API Endpoints ---

@app.post("/oracle/query", tags=["Oracle"])
async def handle_oracle_query(query: OracleQuery):
    """
    Accepts a complex question and orchestrates a swarm of agents to find an answer.
    """
    logger.info(f"Received query for Oracle: '{query.question}' from user: '{query.user_id}'")
    try:
        answer = oracle_instance.query(query.question)
        return {"answer": answer}
    except Exception as e:
        logger.error(f"An error occurred while processing the Oracle query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred in the Oracle.")


@app.post("/webhook", tags=["Telegram"])
async def telegram_webhook(request: Request):
    """
    Handles incoming updates from the Telegram webhook.
    """
    if not telegram_app:
        logger.error("Telegram app not initialized. Cannot process webhook.")
        raise HTTPException(status_code=503, detail="Telegram integration not available.")

    try:
        data = await request.json()
        tg_update = TelegramUpdate.de_json(data, telegram_app.bot)
        logger.debug(f"Received raw update data: {data}")

        if tg_update.message and tg_update.message.text:
            command_text = tg_update.message.text
            chat_id = tg_update.message.chat_id

            logger.info(f"Handling command '{command_text}' for chat_id {chat_id}")

            response_text = katana_bot_instance.handle_command(command_text, str(chat_id))

            if response_text:
                await telegram_app.bot.send_message(chat_id=chat_id, text=response_text)

            return {"status": "ok", "message": "Command processed"}

        return {"status": "ok", "message": "Update received but not actionable"}

    except Exception as e:
        logger.error(f"Error processing webhook update: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error processing update.")

@app.get("/health", tags=["Monitoring"])
async def health_check():
    """Returns a simple health check indicating the API is running."""
    return {"status": "OK", "message": "API is healthy."}

@app.get("/status", tags=["Monitoring"])
async def get_status():
    """Returns a more detailed status of the application."""
    uptime_seconds = time.time() - START_TIME
    uptime_delta = timedelta(seconds=uptime_seconds)

    # ... (rest of the status logic remains the same)

    return {
        "application_status": "running",
        "uptime": str(uptime_delta),
        "version": app.version,
        # ...
    }

if __name__ == "__main__":
    logger.info("Starting KatanaBot API with Uvicorn for local development...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
