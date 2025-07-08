# KatanaBot Agent Instructions

This document provides instructions for developers and agents working with the KatanaBot application, which now uses FastAPI, webhooks for Telegram, and APScheduler for background tasks.

## Overview

The bot has been refactored from a polling-based system to a webhook-based system using FastAPI. This improves efficiency and real-time responsiveness.

-   **FastAPI**: Serves the web application, including the Telegram webhook endpoint and monitoring endpoints.
-   **python-telegram-bot**: Handles interactions with the Telegram Bot API.
-   **APScheduler**: Manages scheduled background tasks (e.g., self-checks, data synchronization).

## Setup and Running

### 1. Dependencies

Ensure all Python dependencies are installed. It's recommended to use a virtual environment.

```bash
pip install -r requirements.txt
```
The `requirements.txt` file has been updated to include:
- `fastapi`
- `uvicorn[standard]` (for running the FastAPI server)
- `python-telegram-bot`
- `apscheduler`

### 2. Environment Variables / Configuration

The application requires two critical pieces of information to be configured in `main.py` (or ideally, via environment variables in a production setup):

-   **`TELEGRAM_BOT_TOKEN`**: Your Telegram Bot Token.
    *   In `main.py`, find the line: `TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"`
    *   Replace `"YOUR_TELEGRAM_BOT_TOKEN"` with your actual bot token.
-   **`WEBHOOK_URL`**: The publicly accessible URL for your webhook.
    *   In `main.py`, find the line: `WEBHOOK_URL = "https://your-actual-domain-or-ngrok-url.com/webhook"`
    *   Replace `"https://your-actual-domain-or-ngrok-url.com/webhook"` with your actual public URL that Telegram will send updates to. This URL must point to the `/webhook` endpoint of your running FastAPI application.

**For local development:**
You can use a tool like `ngrok` to expose your local FastAPI server to the internet.
1.  Start your FastAPI application (see step 3). It will typically run on `http://127.0.0.1:8000`.
2.  Run ngrok: `ngrok http 8000`
3.  Ngrok will provide you with a public HTTPS URL (e.g., `https://<random_string>.ngrok.io`). Use this as your `WEBHOOK_URL` in `main.py` (e.g., `WEBHOOK_URL = "https://<random_string>.ngrok.io/webhook"`).

**Important**: Every time you restart ngrok, you will get a new URL. You must update `WEBHOOK_URL` in `main.py` and restart the FastAPI application for the webhook to be set correctly with Telegram.

### 3. Running the Application

To run the FastAPI application locally:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

-   `main:app`: Tells uvicorn to find the `app` object (FastAPI instance) in the `main.py` file.
-   `--reload`: Enables auto-reloading when code changes (useful for development).
-   `--host 0.0.0.0`: Makes the server accessible from other devices on your network.
-   `--port 8000`: Specifies the port to run on.

Once the application is running, it will attempt to set the Telegram webhook to the `WEBHOOK_URL` you configured. Check the application logs for confirmation or errors.

### 4. Interacting with the Bot

-   Send commands to your bot via Telegram as usual (e.g., `!price BTC-USD`, `!greet`).
-   The bot's responses should now come via the webhook mechanism.

## API Endpoints

The FastAPI application exposes the following utility endpoints:

-   **`/webhook` (POST)**: The endpoint Telegram sends updates to. You generally don't interact with this directly.
-   **`/health` (GET)**: A simple health check. Returns `{"status": "OK", "message": "API is healthy."}`.
    *   Access via: `http://localhost:8000/health`
-   **`/status` (GET)**: Provides detailed status information about the application, including uptime, Telegram integration status, and scheduler status (jobs, next run times).
    *   Access via: `http://localhost:8000/status`
-   **`/uptime` (GET)**: Returns the application's uptime.
    *   Access via: `http://localhost:8000/uptime`
-   **`/docs` (GET)**: FastAPI's automatic interactive API documentation (Swagger UI).
    *   Access via: `http://localhost:8000/docs`
-   **`/redoc` (GET)**: FastAPI's alternative automatic API documentation (ReDoc).
    *   Access via: `http://localhost:8000/redoc`

## Scheduler

-   APScheduler is configured to run background tasks.
-   An example task `scheduled_task_example` is set to run every 5 minutes (configurable in `main.py`). This task logs a message. You can adapt this for actual bot maintenance, self-checks, or periodic data operations.
-   The status of scheduled jobs can be monitored via the `/status` endpoint.

## Logs

-   The application uses Python's `logging` module.
-   Logs are output to the console by default. Check `logging_config.py` for configuration details.
-   Pay attention to logs during startup for information about webhook registration and scheduler initialization.

## Code Structure

-   `main.py`: Contains the FastAPI application, endpoint definitions, Telegram integration logic, and APScheduler setup.
-   `katana_bot.py`: Defines the `KatanaBot` class, which encapsulates the core bot logic (command handling).
-   `katana_agent.py`: (Assumed existing) Contains the `KatanaAgent` logic.
-   `logging_config.py`: Configures logging for the application.
-   `requirements.txt`: Lists Python dependencies.
-   `katana/supabase_client.py`: Initializes and configures the Supabase client.
-   `katana/knowledge_base.py`: Handles fetching data from Supabase and storing it locally.
-   `katana/reporter.py`: Generates weekly reports from the synchronized data.
-   `scripts/sync_supabase.py`: Script executed by the cron job to sync data and trigger reports.
-   `scripts/show_report.py`: CLI tool to display the latest report.
-   `data/supabase_sync/`: Directory where synchronized data and reports are stored (should be in `.gitignore` if it contains sensitive info, though currently stores generated/public data).

## Important Notes for Agents
- When modifying code, ensure that `TELEGRAM_BOT_TOKEN` and `WEBHOOK_URL` are correctly handled. For testing, direct modification in `main.py` is acceptable, but for production, these should be managed via environment variables or a secure configuration system.
- **Supabase Credentials**: For Supabase integration, ensure `SUPABASE_URL` and `SUPABASE_KEY` are available. Locally, these are expected in `secrets.toml`. For GitHub Actions, they are configured as repository secrets.
- If you encounter issues with Telegram updates not being received, verify:
    1. The FastAPI application is running.
    2. The `WEBHOOK_URL` is correctly set and publicly accessible.
    3. Ngrok (if used) is running and the URL matches the one configured.
    4. There are no errors in the application logs related to webhook setup or processing.
- The `katana_bot.py`'s `handle_command` method now returns a string response, which `main.py` then sends back to the user via Telegram. Ensure any new commands follow this pattern.
- Scheduled tasks (like the daily Supabase sync in `.github/workflows/main.yml`) are asynchronous. Be mindful of shared resources if tasks modify bot state or interact with external services. The daily sync script itself is synchronous but runs in a separate GitHub Actions job.
- The weekly report generation can be triggered on-demand via the `!report` Telegram command if a report isn't found. This might take a few seconds.
- Data persistence for knowledge/reflections is currently via JSON files in `data/supabase_sync/`. Consider the implications if this directory is not persistent across deployments or if multiple instances run concurrently (though the cron job is a single executor).
```
