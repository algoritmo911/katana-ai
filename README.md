# Katana AI Platform

This repository contains the services for the Katana AI platform, which includes a task processing pipeline and a Telegram bot.

## Architecture Overview

The platform consists of two main, independent services:

1.  **Task Processing Pipeline**: A robust system for ingesting and executing tasks asynchronously. It uses a FastAPI server to receive tasks, a Redis queue for persistence and buffering, and a dedicated worker process for task execution.
2.  **Telegram Bot**: A flexible Telegram bot for direct interaction and command processing.

---

## 1. Katana Task Pipeline

This service is the core execution engine of the platform.

### How it Works

1.  **API Server (`main.py`)**: A FastAPI application listens for incoming tasks on a webhook endpoint.
2.  **Redis Queue**: When tasks are received, the API server immediately places them into a Redis list, which acts as a task queue. This provides a fast response to the client (e.g., n8n) and ensures tasks are not lost.
3.  **Worker (`worker.py`)**: A separate, asynchronous Python process constantly listens to the Redis queue. When a new task appears, the worker picks it up and "executes" it (currently, execution is simulated by logging the task content).

### Running the Pipeline Locally

#### Prerequisites

-   Python 3.8+
-   pip (Python package installer)
-   A running Redis server.

#### 1. Install Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

#### 2. Configure Environment Variables

Copy the example environment file and edit it if your Redis server is not on localhost.

```bash
cp .env.example .env
```

Your `.env` file should contain the Redis configuration:

```env
# .env
REDIS_HOST="localhost"
REDIS_PORT="6379"
REDIS_DB="0"
REDIS_QUEUE_NAME="katana_task_queue"
```

#### 3. Run the Services

You need to run two processes in separate terminals.

**Terminal 1: Run the API Server**

```bash
python main.py
```

The API server will start on `http://localhost:8000`.

**Terminal 2: Run the Worker**

```bash
python worker.py
```

The worker will connect to Redis and start listening for tasks.

### API Endpoints

#### Health Check

-   **Endpoint**: `/health`
-   **Method**: `GET`
-   **Description**: Checks the status of the API and its connection to Redis. Returns a `200 OK` if both are healthy, or a `503 Service Unavailable` if the Redis connection fails.

#### n8n Task Webhook

This endpoint is designed to receive tasks from an external service like n8n.

-   **Endpoint**: `/n8n/webhook`
-   **Method**: `POST`
-   **Description**: Accepts a list of tasks and places them onto the Redis queue for the worker to process.
-   **Request Body**: A JSON object with a single key, `tasks`, which is an array of strings.

**Example `curl` command:**

```bash
curl -X POST "http://localhost:8000/n8n/webhook" \
-H "Content-Type: application/json" \
-d '{
  "tasks": [
    "Analyze the latest user feedback on the new feature.",
    "Generate a summary report of the week''s activities."
  ]
}'
```

---

## 2. Katana Telegram Bot

This is a Telegram bot designed for flexible interaction and command processing.

### Running the Bot Locally

Follow steps 1 and 2 from the Pipeline setup to install dependencies and create your `.env` file. Then, add your Telegram token to `.env`:

```env
# .env
KATANA_TELEGRAM_TOKEN="YOUR_TELEGRAM_BOT_TOKEN" # Get this from BotFather on Telegram
ANTHROPIC_API_KEY="YOUR_ANTHROPIC_API_KEY"     # Optional
OPENAI_API_KEY="YOUR_OPENAI_API_KEY"         # Optional
```

**Run the Bot:**

Execute the local runner script for the bot:

```bash
python run_bot_locally.py
```

### Bot Features

-   **Continuous Polling**: Resilient to minor errors and network issues.
-   **Error Handling**: Catches and logs exceptions without crashing.
-   **Liveness Monitoring**: Includes a heartbeat mechanism to monitor if the bot is active (see `tools/check_heartbeat.py`).
-   **Deployment Options**: Includes sample configurations for `systemd` and `logrotate` for production deployments. For full details, see the `deploy/` directory.

## Project Structure

-   `main.py`: The entry point for the FastAPI Task Ingestion API.
-   `worker.py`: The entry point for the task processing worker.
-   `bot/`: Contains the core logic for the Telegram bot.
-   `src/`: Shared source code (currently minimal).
-   `tests/`: Contains all automated tests.
-   `requirements.txt`: Python dependencies for all services.
-   `.env.example`: Example file for all environment variable configurations.
-   `deploy/`: Contains deployment scripts and configurations (mostly for the bot).
