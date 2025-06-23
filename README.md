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
    *   `REDIS_URL`: The connection URL for your Redis instance. This is used for the bot's short-term memory. Defaults to `redis://localhost:6379/0` if not set. Example: `redis://username:password@your-redis-host:6379/0`.

    **Optional Variables:**
    *   `USE_LLM_NLP` (optional): Set to `true` to attempt using a (currently placeholder) LLM for NLP. Defaults to `false` (uses basic keyword matching).

    **Methods to Set Environment Variables:**

    **a) Using a `.env` file (Recommended for Development):**
    Create a file named `.env` in the root of the project:
    ```env
    TELEGRAM_API_TOKEN="your_telegram_token_here"
    OPENAI_API_KEY="your_openai_key_here"
    REDIS_URL="redis://localhost:6379/0" # Or your custom Redis URL
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

## Setting up Redis (for Short-Term Memory)

The bot uses Redis for short-term memory, such as remembering recent conversation history for context with GPT.

**1. Installation:**

   *   **Docker (Recommended for ease of use):**
       If you have Docker installed, you can easily run a Redis instance:
       ```bash
       docker run -d --name katana-redis -p 6379:6379 redis/redis-stack-server:latest
       ```
       This command will:
       - Download the Redis Stack server image (which includes RedisJSON, RedisSearch, etc., though only core Redis is used for now).
       - Run it in detached mode (`-d`).
       - Name the container `katana-redis`.
       - Map port `6379` on your host to port `6379` in the container.

       To stop the container: `docker stop katana-redis`
       To start it again: `docker start katana-redis`
       To remove it (e.g., if you want to start fresh): `docker rm katana-redis` (after stopping it)

   *   **Native Installation:**
       Alternatively, you can install Redis directly on your system. Follow the official instructions for your operating system: [Redis Installation Guide](https://redis.io/docs/latest/operate/oss_and_stack/install/install-redis/)

**2. Configuration:**

   Ensure the `REDIS_URL` environment variable is set correctly (see "Set up environment variables" above). If you're running Redis locally with default settings and no password, `redis://localhost:6379/0` should work.

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

Log files are stored in the `logs/` directory.
Command files are stored in the `commands/` directory.
Temporary voice files are stored in `voice_temp/` during processing.