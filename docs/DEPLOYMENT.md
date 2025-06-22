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

## Running as a Service (Production)

For production deployments, it's highly recommended to run the Katana Bot as a managed service to ensure it restarts automatically on failure or after a server reboot. Below are examples for `systemd` (common on modern Linux distributions) and `supervisor`.

### Using systemd

1.  **Create a service file:**
    Create a file named `katana_bot.service` in `/etc/systemd/system/`.
    You can use the example file `docs/examples/katana_bot.service` as a template. Copy it and modify the paths and user settings:
    ```bash
    sudo cp docs/examples/katana_bot.service /etc/systemd/system/katana_bot.service
    sudo nano /etc/systemd/system/katana_bot.service # Edit paths and user
    ```
    Ensure you set `User`, `Group`, `WorkingDirectory`, and `ExecStart` correctly. Also, choose a method for providing environment variables (direct `Environment=` lines or `EnvironmentFile=`). If using `EnvironmentFile`, ensure it's secured.

2.  **Reload systemd daemon:**
    ```bash
    sudo systemctl daemon-reload
    ```

3.  **Enable the service (to start on boot):**
    ```bash
    sudo systemctl enable katana_bot.service
    ```

4.  **Start the service:**
    ```bash
    sudo systemctl start katana_bot.service
    ```

5.  **Check service status:**
    ```bash
    sudo systemctl status katana_bot.service
    journalctl -u katana_bot.service -f # To follow logs
    ```

### Using Supervisor

1.  **Install Supervisor:**
    ```bash
    sudo apt-get install supervisor # Debian/Ubuntu
    # Or using pip: pip install supervisor
    ```

2.  **Create a configuration file:**
    Create a file named `katana_bot.conf` in Supervisor's configuration directory (e.g., `/etc/supervisor/conf.d/katana_bot.conf`).
    Use the example file `docs/examples/katana_bot.conf` as a template. Copy and modify paths, user, and environment settings:
    ```bash
    sudo cp docs/examples/katana_bot.conf /etc/supervisor/conf.d/katana_bot.conf
    sudo nano /etc/supervisor/conf.d/katana_bot.conf # Edit paths, user, command, environment
    ```
    Ensure log file paths are writable by the specified user.

3.  **Update Supervisor:**
    Tell Supervisor to read the new configuration and update:
    ```bash
    sudo supervisorctl reread
    sudo supervisorctl update
    ```

4.  **Check process status:**
    ```bash
    sudo supervisorctl status katana_bot
    sudo supervisorctl tail -f katana_bot stdout # To follow stdout logs
    sudo supervisorctl tail -f katana_bot stderr # To follow stderr logs
    ```

## Monitoring

### Heartbeat Mechanism

The Katana Bot implements a simple file-based heartbeat to indicate it's running.
*   The bot (specifically `bot/katana_bot.py`) attempts to write the current timestamp to a file named `katana_heartbeat.txt` in the project's root directory each time its main polling loop starts or restarts.
*   If this file is not updated regularly, it might indicate that the bot process has crashed in a way that systemd/supervisor didn't restart it, or that the polling loop itself is hung (though the current heartbeat implementation primarily signals loop *restarts* rather than continuous liveness within a single blocking poll).

### Heartbeat Check Script

A script `tools/check_heartbeat.py` is provided to check the freshness of the heartbeat file.

**Usage:**
```bash
python tools/check_heartbeat.py [--file /path/to/katana_heartbeat.txt] [--threshold SECONDS]
```
*   `--file`: Path to the `katana_heartbeat.txt` file. Defaults to `../katana_heartbeat.txt` (assuming run from `tools/` relative to project root).
*   `--threshold`: Maximum allowed age of the heartbeat in seconds. Defaults to 120 seconds.

The script will:
*   Print an "OK" message and exit with status 0 if the heartbeat is fresh.
*   Print a "CRITICAL" message to stderr and exit with status 1 if the heartbeat file is not found, empty, unreadable, or stale.

**Automated Checking (Cron Example):**
You can schedule this script to run periodically using cron to monitor the bot's health.
Open your crontab for editing:
```bash
crontab -e
```
Add a line like this to run the check every 5 minutes:
```cron
*/5 * * * * /usr/bin/python3 /path/to/your/katana-bot-project/tools/check_heartbeat.py --file /path/to/your/katana-bot-project/katana_heartbeat.txt --threshold 300 >> /var/log/katana_bot/heartbeat_check.log 2>&1
```
*   Adjust paths and the Python interpreter path as needed.
*   The threshold (e.g., 300 seconds = 5 minutes) should be greater than the heartbeat update interval plus some buffer.
*   This example logs the output of the check script. For active alerting, you would modify `check_heartbeat.py` or pipe its output to a notification service.

### Extending for Active Notifications
The `check_heartbeat.py` script currently logs to stderr on failure. To implement active notifications (e.g., email, Telegram message):
1.  Modify `check_heartbeat.py` to include logic for sending notifications using appropriate libraries (e.g., `smtplib` for email, or `python-telegram-bot` to send a message via another bot).
2.  Ensure the script has the necessary configurations (SMTP server details, Telegram bot token for notifications, recipient addresses/chat IDs). These should also be managed securely.
```
