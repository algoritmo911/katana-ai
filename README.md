# katana-ai

A Telegram bot that can understand text and voice commands.

## Features

-   Processes text commands (JSON and natural language).
-   **NEW**: Processes voice commands by transcribing them to text using OpenAI Whisper.
-   Basic NLP for mapping natural language to shell commands.
-   Saves structured commands to the filesystem.

## Setup

1.  **Clone the repository.**
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Set up environment variables:**
    Create a `.env` file in the root directory or set the following environment variables:
    *   `TELEGRAM_API_TOKEN`: Your Telegram Bot API token.
    *   `OPENAI_API_KEY`: Your OpenAI API key (required for voice message processing).
    *   `USE_LLM_NLP` (optional): Set to `true` to attempt using a (currently placeholder) LLM for NLP. Defaults to `false` (uses basic keyword matching).

    Example `.env` file:
    ```
    TELEGRAM_API_TOKEN="your_telegram_token_here"
    OPENAI_API_KEY="your_openai_key_here"
    USE_LLM_NLP="false"
    ```

4.  **Run the bot:**
    ```bash
    python bot.py
    ```

## Usage

-   Send text messages with commands (e.g., "покажи место на диске").
-   Send voice messages with commands. The bot will transcribe the voice and process the text.
-   Send structured JSON commands (see `bot.py` for format details).

## Logging

Log files are stored in the `logs/` directory.
Command files are stored in the `commands/` directory.
Temporary voice files are stored in `voice_temp/` during processing.