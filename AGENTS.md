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

### 2. Environment Variables / Configuration with Doppler

The application requires critical information to be provided as environment variables. These are managed using **Doppler**.

-   **`TELEGRAM_BOT_TOKEN`**: Your Telegram Bot Token.
-   **`WEBHOOK_URL`**: The publicly accessible URL for your webhook.
-   *(Other secrets as defined in `secrets.toml.example` or your Doppler project configuration, e.g., `COINBASE_API_KEY`, `COINBASE_API_SECRET`)*

These variables are no longer set directly in `main.py`. Instead, they are injected into the application's environment by Doppler.

**For local development:**
1.  Install the Doppler CLI (see `README.md` for instructions).
2.  Log in to Doppler: `doppler login`
3.  Set up your project: `doppler setup` (follow prompts to select the project and config).
4.  If using `ngrok` to expose your local FastAPI server:
    *   Start your FastAPI application (prefixed with Doppler, see step 3). It will typically run on `http://127.0.0.1:8000`.
    *   Run ngrok: `ngrok http 8000`
    *   Ngrok will provide a public HTTPS URL (e.g., `https://<random_string>.ngrok.io`).
    *   **Important**: Update the `WEBHOOK_URL` secret in your Doppler project configuration with this ngrok URL. Doppler will then inject the correct URL when you run the app. Restart the FastAPI application after updating the secret in Doppler.

### 3. Running the Application with Doppler

To run the FastAPI application locally with secrets injected by Doppler:

```bash
doppler run -- uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

-   `doppler run --`: This command fetches the secrets from your Doppler project and injects them as environment variables before running the subsequent command (`uvicorn ...`).
-   `main:app`, `--reload`, `--host`, `--port`: Standard uvicorn arguments.

Once the application is running (with secrets from Doppler), it will attempt to set the Telegram webhook using the `WEBHOOK_URL` provided by Doppler. Check the application logs for confirmation or errors.

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

## Important Notes for Agents
- When modifying code, ensure that `TELEGRAM_BOT_TOKEN` and `WEBHOOK_URL` (and any other necessary secrets) are defined in your Doppler project. The application now relies solely on environment variables provided by Doppler for these configurations.
- If you encounter issues with Telegram updates not being received, verify:
    1. The FastAPI application is running (using `doppler run -- ...`).
    2. The `WEBHOOK_URL` in your Doppler configuration is correct and publicly accessible.
    3. Ngrok (if used for local development) is running and its URL is correctly updated in Doppler.
    4. There are no errors in the application logs related to webhook setup or processing.
- The `katana_bot.py`'s `handle_command` method now returns a string response, which `main.py` then sends back to the user via Telegram. Ensure any new commands follow this pattern.
- Scheduled tasks are asynchronous. Be mindful of shared resources if tasks modify bot state or interact with external services.
```
