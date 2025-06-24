# Telegram Receiver Bot

This bot acts as a simple, passive receiver for messages from Telegram. It listens for text messages, voice messages, and documents. Upon receiving any of these, it logs the message metadata (and text content for text messages) to a local file (`received_messages.log`).

The primary purpose of this bot is to act as a lightweight frontend for data ingestion. The actual processing of the received data is intended to be handled by downstream services or AI nodes that can consume the `received_messages.log` file or be triggered by other mechanisms (e.g., a file watcher).

## Features

-   Receives text messages.
-   Receives voice messages (saves `file_id` for later retrieval).
-   Receives documents (saves `file_id` for later retrieval).
-   Logs received message information to `received_messages.log` in JSON Lines format.
-   Basic logging for monitoring bot activity.

## Setup

1.  **Clone the repository (if you haven't already).**
2.  **Navigate to the bot directory:**
    ```bash
    cd telegram_receiver_bot
    ```
3.  **Create a virtual environment (recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
4.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
5.  **Set the Telegram Bot Token:**
    You need a token from BotFather on Telegram. Set it as an environment variable:
    ```bash
    export TELEGRAM_BOT_TOKEN="YOUR_ACTUAL_BOT_TOKEN"
    ```
    Replace `"YOUR_ACTUAL_BOT_TOKEN"` with the token you received. Do not commit your token to version control.

## Running the Bot

Once the setup is complete, you can run the bot using:

```bash
python bot.py
```

The bot will start listening for messages. Any received text, voice, or document messages will be logged to `telegram_receiver_bot/received_messages.log`.

## Log Format (`received_messages.log`)

The `received_messages.log` file contains one JSON object per line (JSON Lines format). Each object represents a received message and has the following structure:

**For text messages:**
```json
{
  "type": "text",
  "timestamp": "YYYY-MM-DDTHH:MM:SS.ffffffZ", // UTC timestamp
  "message_id": 123,
  "chat_id": 4567890,
  "user_id": 1234567,
  "text": "Hello, world!"
}
```

**For voice messages:**
```json
{
  "type": "voice",
  "timestamp": "YYYY-MM-DDTHH:MM:SS.ffffffZ",
  "message_id": 124,
  "chat_id": 4567890,
  "user_id": 1234567,
  "file_id": "FILE_ID_PROVIDED_BY_TELEGRAM",
  "file_unique_id": "UNIQUE_FILE_ID",
  "duration": 60, // seconds
  "mime_type": "audio/ogg",
  "file_size": 50000 // bytes
}
```

**For document messages:**
```json
{
  "type": "document",
  "timestamp": "YYYY-MM-DDTHH:MM:SS.ffffffZ",
  "message_id": 125,
  "chat_id": 4567890,
  "user_id": 1234567,
  "file_id": "FILE_ID_PROVIDED_BY_TELEGRAM",
  "file_unique_id": "UNIQUE_FILE_ID",
  "file_name": "example.pdf", // Optional, might not always be present
  "mime_type": "application/pdf", // Optional
  "file_size": 120000 // bytes, optional
}
```

This log file can then be used as an input source for other processing systems.Tool output for `create_file_with_block`:
