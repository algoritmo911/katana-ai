import logging
import time
from datetime import timedelta
from fastapi import FastAPI, Request, HTTPException
import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from katana.routing.signal_hub import SignalHub
from katana.interfaces.interface_telegram import TelegramInterface
from logging_config import setup_logging

# Configure logging
setup_logging(logging.DEBUG)
logger = logging.getLogger(__name__)

# --- Application Setup ---
app = FastAPI(title="KatanaBot API", version="0.2.0")
START_TIME = time.time()

# Initialize SignalHub and Interfaces
signal_hub = SignalHub()

# --- Telegram Bot Setup ---
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
WEBHOOK_URL = "https://your-actual-domain-or-ngrok-url.com/webhook"

telegram_interface = None

# --- Scheduler Job ---
async def scheduled_task_example():
    logger.info("Scheduled task executed.")

# --- FastAPI Event Handlers ---
@app.on_event("startup")
async def startup_event():
    global telegram_interface, scheduler

    if TELEGRAM_BOT_TOKEN and TELEGRAM_BOT_TOKEN != "YOUR_TELEGRAM_BOT_TOKEN":
        telegram_interface = TelegramInterface(TELEGRAM_BOT_TOKEN, WEBHOOK_URL, signal_hub.dispatcher)
        await telegram_interface.set_webhook()

    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        scheduled_task_example,
        trigger=IntervalTrigger(seconds=300),
        id="periodic_self_check",
        name="Periodic Self-Check/Sync",
        replace_existing=True
    )
    scheduler.start()
    logger.info("FastAPI application startup sequence complete.")

@app.on_event("shutdown")
async def shutdown_event():
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)

# --- API Endpoints ---
@app.post("/webhook")
async def telegram_webhook(request: Request):
    if not telegram_interface:
        raise HTTPException(status_code=503, detail="Telegram integration not available.")

    try:
        data = await request.json()
        await telegram_interface.handle_update(data)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error processing webhook update: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.get("/health")
async def health_check():
    return {"status": "OK"}

@app.get("/status")
async def get_status():
    uptime_seconds = time.time() - START_TIME
    uptime_delta = timedelta(seconds=uptime_seconds)
    return {"uptime": str(uptime_delta)}

if __name__ == "__main__":
    logger.info("Starting KatanaBot API with Uvicorn...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
