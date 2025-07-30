# katana-ai

A Telegram bot that can understand text and voice commands.

## Features

-   Processes text commands (JSON and natural language).
    -   Enhanced NLP with synonym recognition (e.g., "привет", "здорово", "добрый день" are all understood as greetings).
    -   Support for new commands like asking for weather or a joke (current implementation uses placeholders).
-   Processes voice commands by transcribing them to text using OpenAI Whisper.
-   Dynamic and personalized responses:
    -   Greets users by name (if available) and time of day.
    -   Includes bot usage statistics in responses.
-   Improved error handling with polite fallback messages.
-   Saves structured JSON commands to the filesystem.
-   Basic NLP for mapping natural language to shell commands (e.g., "покажи место на диске" -> `df -h`).

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

-   **Text Messages**:
    -   Send natural language commands (e.g., "сколько места на диске?", "какая сейчас погода?", "расскажи анекдот", "привет бот").
    -   The bot understands various synonyms and phrasing.
    -   Send structured JSON commands (see `bot.py` for format details if needed, though natural language is preferred).
-   **Voice Messages**:
    -   Send voice messages with commands. The bot will transcribe the voice to text and process it like a text command.
-   **Interaction**:
    -   The bot will respond with personalized greetings and include usage statistics.
    -   If a command isn't understood, the bot will provide a polite fallback message.

### Personalization Features

-   **Command History**: The bot now saves your command history.
-   **Command Recommendations**:
    -   Send the `/recommendations` command to the bot to get a list of your most frequently used commands.

## CLI Usage

A command-line interface is available for managing user data.

-   **View User Preferences**:
    ```bash
    python katana_cli.py user-prefs <user_id>
    ```
-   **Get Command Recommendations**:
    ```bash
    python katana_cli.py user-recs <user_id> [--top-n <number>]
    ```

## Logging

Log files are stored in the `logs/` directory.
Command files are stored in the `commands/` directory.
Temporary voice files are stored in `voice_temp/` during processing.
User data is stored in the `user_data/` directory.

## Observability

The bot exposes two endpoints for monitoring:

*   **/api/katana/health**: Returns the health status and uptime of the bot.
*   **/api/katana/stats**: Returns a JSON object with various statistics, including:
    *   `uptime`: The uptime of the bot.
    *   `commands_received`: The number of commands received by the bot.
    *   `last_command_ts`: The timestamp of the last command received.
    *   `dry_run`: Whether the bot is in dry-run mode.
    *   `build_version`: The build version of the bot.
    *   `last_command_echo`: The last command received by the bot.