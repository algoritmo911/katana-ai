# Telegram Receiver Bot

This bot acts as a message receiver from Telegram and transforms them into commands for the Katana AI project. It listens for text, voice, and document messages. Upon receiving a message, it formats it into a structured command and appends it to the central command file used by the Katana agent.

The primary purpose of this bot is to serve as the main entry point for data ingestion into the Katana AI ecosystem. It populates `../alg911.catana-ai/katana.commands.json` with new tasks for the agent to process.

## Features

-   Receives text, voice, and document messages.
-   Formats each message into a structured JSON command.
-   Appends the command to `../alg911.catana-ai/katana.commands.json`.
-   Includes metadata such as `command_id`, `timestamp_utc`, and `source`.
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
    You need a token from @BotFather on Telegram. Set it as an environment variable:
    ```bash
    export TELEGRAM_BOT_TOKEN="YOUR_ACTUAL_BOT_TOKEN"
    ```
    Replace `"YOUR_ACTUAL_BOT_TOKEN"` with the token you received. Do not commit your token to version control.

## Running the Bot

Once the setup is complete, you can run the bot using:

```bash
python bot.py
```

The bot will start listening for messages. Any received text, voice, or document messages will be formatted and saved as commands in `../alg911.catana-ai/katana.commands.json`.

## Command Format (`katana.commands.json`)

The `katana.commands.json` file is a JSON array where each element is a command object. The bot adds new commands to this array. Each command has the following structure:

```json
{
  "command_id": "a-unique-uuid-string",
  "timestamp_utc": "YYYY-MM-DDTHH:MM:SS.ffffff+00:00",
  "source": "telegram",
  "command_type": "ingest_message",
  "payload": {
    // The content of the payload varies by message type
  }
}
```

### Payload for Text Messages

```json
"payload": {
  "type": "text",
  "message_id": 123,
  "chat_id": 4567890,
  "user_id": 1234567,
  "text": "Hello, world!"
}
```

### Payload for Voice Messages

```json
"payload": {
  "type": "voice",
  "message_id": 124,
  "chat_id": 4567890,
  "user_id": 1234567,
  "file_id": "FILE_ID_PROVIDED_BY_TELEGRAM",
  "file_unique_id": "UNIQUE_FILE_ID",
  "duration": 60,
  "mime_type": "audio/ogg",
  "file_size": 50000
}
```

### Payload for Document Messages

```json
"payload": {
  "type": "document",
  "message_id": 125,
  "chat_id": 4567890,
  "user_id": 1234567,
  "file_id": "FILE_ID_PROVIDED_BY_TELEGRAM",
  "file_unique_id": "UNIQUE_FILE_ID",
  "file_name": "example.pdf",
  "mime_type": "application/pdf",
  "file_size": 120000
}
```

This file is the primary input for the `katana_agent.py` script, which processes these commands.
