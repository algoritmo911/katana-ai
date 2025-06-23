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
    The bot uses environment variables for configuration. These can be set directly in your environment or by creating a `.env` file in the root project directory.

    **Required Variables:**
    *   `TELEGRAM_API_TOKEN`: Your Telegram Bot API token. Get this from BotFather on Telegram.
    *   `OPENAI_API_KEY`: Your OpenAI API key. This is **strictly required for voice message processing**. Without it, voice messages will not be understood. You can obtain a key from [platform.openai.com](https://platform.openai.com/).

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

## Logging

Log files are stored in the `logs/` directory.
Command files are stored in the `commands/` directory.
Temporary voice files are stored in `voice_temp/` during processing.