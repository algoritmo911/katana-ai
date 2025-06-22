# Katana Bot Deployment Guide

This document provides instructions for deploying and running the Katana Bot.

## Prerequisites

*   Python 3.9+
*   pip (Python package installer)

## Setup

1.  **Clone the Repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Install Dependencies:**
    It's recommended to use a virtual environment.
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```
    *(Note: A `requirements.txt` file should be generated and maintained for the project. For now, the necessary libraries identified during development are: `pyTelegramBotAPI`, `anthropic`, `openai`)*.
    To install them manually if `requirements.txt` is not yet created:
    ```bash
    pip install pyTelegramBotAPI anthropic openai
    ```

3.  **Set Environment Variables:**
    The bot requires several API keys and configuration options to be set as environment variables.

    *   `KATANA_TELEGRAM_TOKEN`: Your Telegram Bot Token obtained from BotFather.
        *   Format: `1234567890:ABCDEFGHIJKLMnopqrstuvwxyz123456789`
    *   `ANTHROPIC_API_KEY`: Your API key for the Anthropic (Claude) API.
    *   `OPENAI_API_KEY`: Your API key for the OpenAI API.

    Set these variables in your environment. For example, in Linux/macOS:
    ```bash
    export KATANA_TELEGRAM_TOKEN="your_telegram_token"
    export ANTHROPIC_API_KEY="your_anthropic_api_key"
    export OPENAI_API_KEY="your_openai_api_key"
    ```
    For production deployments, consider using a `.env` file with a library like `python-dotenv` (though this is not currently implemented in the bot's loading mechanism) or your deployment platform's secret management tools.

## Running the Bot

1.  **Ensure Environment Variables are Set:** Verify that all required API keys are available in the environment where the bot will run.
2.  **Navigate to the Bot Directory:**
    If you are in the project root:
    ```bash
    cd bot
    ```
3.  **Run the Bot Script:**
    ```bash
    python katana_bot.py
    ```
    The bot will start polling for messages. You should see log output in the console indicating the bot has started and is attempting to poll.

    Example startup log messages:
    ```
    YYYY-MM-DD HH:MM:SS,sss - bot.katana_bot - INFO - Initializing Katana Bot...
    YYYY-MM-DD HH:MM:SS,sss - bot.katana_bot - INFO - Telegram API Token loaded successfully (masked: 123...:XYZ).
    YYYY-MM-DD HH:MM:SS,sss - bot.katana_bot - INFO - TeleBot instance created successfully.
    YYYY-MM-DD HH:MM:SS,sss - bot.katana_bot - INFO - Attempting to start bot polling...
    YYYY-MM-DD HH:MM:SS,sss - bot.katana_bot - INFO - Bot polling started with none_stop=True.
    ```

## Logging and Monitoring

*   The bot logs events to standard output (console). This includes:
    *   Bot initialization status.
    *   Polling start and errors.
    *   Received messages (ChatID, UserID, Text).
    *   Command validation results.
    *   NLP client processing (which client, prompt summary, success/error).
    *   Errors encountered during message handling, including tracebacks for unexpected errors.
*   For production, it's recommended to redirect standard output and standard error to log files or a centralized logging system (e.g., systemd journal, Docker logs, cloud logging services).
    Example (simple file redirection):
    ```bash
    python katana_bot.py > katana_bot.log 2>&1 &
    ```

## Updating the Bot

1.  **Stop the Bot:** If running, stop the current bot process (e.g., `Ctrl+C` if running in the foreground, or using process management tools like `kill`).
2.  **Pull Latest Changes:**
    ```bash
    git pull origin dev  # Or the relevant branch
    ```
3.  **Update Dependencies (if `requirements.txt` changed):**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Restart the Bot:** Follow the "Running the Bot" instructions.

## Security Recommendations for API Keys

*   **Never hardcode API keys directly into the source code.** Use environment variables as implemented.
*   **Restrict API Key Permissions:** If your API provider allows, create API keys with the minimum necessary permissions for the bot's functionality.
*   **Environment Variables in Production:**
    *   For Docker deployments, pass environment variables securely to the container.
    *   For PaaS (Platform as a Service) deployments (e.g., Heroku, AWS Elastic Beanstalk), use the platform's provided mechanisms for setting environment variables or secrets.
    *   For server deployments, set environment variables in the shell profile of the user running the bot, or use systemd service files with `Environment=` directives, or tools like `direnv`.
*   **Do not commit `.env` files (if used for local development) to version control.** Add `.env` to your `.gitignore` file.
*   **Regularly review and rotate API keys** if suspicious activity is detected or as part of a security policy.
```
