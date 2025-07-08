# katana-ai

A Telegram bot that can understand text and voice commands.

## Features

-   Processes text commands (JSON and natural language).
-   Processes voice commands by transcribing them to text using OpenAI Whisper.
-   **NEW**: Real-time, streamed responses from GPT for general queries and non-command text.
-   Basic NLP for mapping natural language to shell commands.
-   Saves structured commands to the filesystem.

## Setup

1.  **Clone the repository.**
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Set up environment variables:**
    The bot uses environment variables for configuration. These can be set directly in your environment or by creating a `.env` file in the root project directory.

    **Required Variables:**
    *   `TELEGRAM_API_TOKEN`: Your Telegram Bot API token. Get this from BotFather on Telegram.
    *   `OPENAI_API_KEY`: Your OpenAI API key. This is **strictly required for voice message processing and GPT-based text generation**. Without it, voice messages will not be understood and general queries will not receive GPT responses. You can obtain a key from [platform.openai.com](https://platform.openai.com/).

    **Optional Variables:**
    *   `USE_LLM_NLP` (optional): Set to `true` to attempt using a (currently placeholder) LLM for NLP. Defaults to `false` (uses basic keyword matching).

    **Methods to Set Environment Variables:**

    **a) Using a `.env` file (Recommended for Development):**
    Create a file named `.env` in the root of the project:
    ```env
    TELEGRAM_API_TOKEN="your_telegram_token_here"
    OPENAI_API_KEY="your_openai_key_here"
    # USE_LLM_NLP="false" # Optional, defaults to false
    ```
    **Important:** Add `.env` to your `.gitignore` file to prevent accidentally committing your API keys.

    **b) Setting directly in your shell (Current Session Only):**
    *   For Linux/macOS (bash/zsh):
        ```bash
        export TELEGRAM_API_TOKEN="your_telegram_token_here"
        export OPENAI_API_KEY="your_openai_key_here"
        ```
    *   For Windows (Command Prompt):
        ```cmd
        set TELEGRAM_API_TOKEN="your_telegram_token_here"
        set OPENAI_API_KEY="your_openai_key_here"
        ```
    *   For Windows (PowerShell):
        ```powershell
        $env:TELEGRAM_API_TOKEN="your_telegram_token_here"
        $env:OPENAI_API_KEY="your_openai_key_here"
        ```

    **c) Setting persistently (Linux/macOS):**
    You can add the `export` commands to your shell's profile script (e.g., `~/.bashrc`, `~/.zshrc`, or `~/.profile`). For example, add to `~/.bashrc`:
    ```bash
    echo 'export OPENAI_API_KEY="your_openai_key_here"' >> ~/.bashrc
    echo 'export TELEGRAM_API_TOKEN="your_telegram_token_here"' >> ~/.bashrc
    source ~/.bashrc
    ```
    Remember to replace `"your_key_here"` with your actual keys.

    **Security Note:** Never hardcode your API keys directly into your scripts or commit them to version control systems like Git.

4.  **Run the bot:**
    ```bash
    python bot.py
    ```

## Usage

-   Send text messages with commands (e.g., "покажи место на диске").
-   Send voice messages with commands. The bot will transcribe the voice and process the text.
-   Send structured JSON commands (see `bot.py` for format details).
-   Send general text queries (e.g., "расскажи анекдот" or "what is quantum physics?"). The bot will stream a response from GPT.

## GPT Streaming and Interaction

If a message sent to the bot is not recognized as a specific NLP command (like "check disk space") or a valid JSON-formatted command, the bot will forward the text to an OpenAI GPT model (currently GPT-3.5-Turbo) to generate a response.

**How it works:**
-   The bot will indicate it's working by showing a 'typing...' status in Telegram.
-   The response from GPT will be streamed back to you. This means the message will appear and then update in real-time as more parts of the response are generated, similar to how you see responses in ChatGPT.
-   This provides a more natural and immediate feedback loop for longer answers.

**Requirements:**
-   A valid `OPENAI_API_KEY` must be configured in your environment variables for this feature to work.

## Logging

Log files are stored in the `logs/` directory:
- `telegram.log`: General bot operational logs.
- `commands.log`: Logs related to specific command events (older format).
- `command_telemetry.log`: Detailed telemetry for decorated commands (JSON format).

Command files are stored in the `commands/` directory.
Temporary voice files are stored in `voice_temp/` during processing.

## Command Telemetry & Self-Analysis

The bot includes a module for Command Telemetry and Self-Analysis. Key functions and CLI commands are decorated with `@trace_command` to automatically log detailed information about their execution.

**Features:**

-   **Automatic Logging**: Each decorated command/handler logs:
    -   `trace_id`: A unique ID for each command invocation.
    -   `log_event_timestamp_utc`: ISO timestamp when the log entry was created.
    -   `command_start_time_utc`: ISO timestamp when the command execution began.
    -   `user`: Information about the user invoking the command.
        -   For Telegram commands: `{"id": <user_id>, "username": <username>, "source": "telegram"}`
        -   For system/CLI commands: `{"username": <system_username>, "source": "system"}`
    -   `command_name`: The name of the executed command/function (e.g., `ClassName.method_name` or `function_name`).
    -   `arguments`: Positional (`args`) and keyword (`kwargs`) arguments passed to the command (sensitive data may be present).
    -   `success`: Boolean indicating if the command executed successfully.
    -   `execution_time_seconds`: Duration of the command execution.
    -   `result`: The return value of the command if successful (serialized, sensitive data may be present).
    -   `error`: Details of any exception raised if the command failed (includes `type`, `message`, and `details`).
    -   `tags`: Optional custom key-value pairs for analytics (e.g., `{"command_type": "slash"}`).
-   **Log File**: All telemetry data is logged in JSON format to `logs/command_telemetry.log`, with each entry on a new line.
-   **Decorator Usage**:
    -   Basic: `@trace_command`
    -   With tags: `@trace_command(tags={"category": "financial", "priority": "high"})`

This structured logging is designed for monitoring, debugging, and future analytics or self-analysis capabilities.