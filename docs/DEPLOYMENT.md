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
    journalctl -u katana_bot.service -f # To follow logs (-n 100 to see last 100 lines)
    ```
    *   **Log Management**: By default, `systemd` uses `journald`. You can configure `journald` (e.g., in `/etc/systemd/journald.conf`) for persistence, rotation, and size limits. If you chose file-based logging in the `.service` file (e.g., `StandardOutput=append:/var/log/katana_bot/katana_bot.log`), ensure the directory exists and `your_user` has write permissions. Log rotation for files would then need to be managed separately (e.g., with `logrotate`).

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
    *   **Log Management**: Supervisor handles log rotation for files specified by `stdout_logfile` and `stderr_logfile` based on `stdout_logfile_maxbytes` and `stdout_logfile_backups` (and similarly for stderr). Ensure the log directories (e.g., `/path/to/your/katana-bot-project/logs/` or `/var/log/katana_bot/`) exist and are writable by the user running the Supervisor process or the user specified in the `katana_bot.conf`.

### Graceful Shutdown
The bot is configured to handle `SIGINT` (Ctrl+C) and `SIGTERM` (standard termination signal from systemd/supervisor) for a graceful shutdown. It will attempt to stop polling and log its shutdown process. This ensures cleaner exits when managed by a service manager.

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
The `check_heartbeat.py` script currently logs to stderr and simulates alert messages. To implement active notifications:

*   **Option 1: Wrapper Script (Simple)**
    You can create a small shell script that runs `check_heartbeat.py` and then, based on its exit code, sends a notification.
    Example `run_heartbeat_check_and_alert.sh`:
    ```bash
    #!/bin/bash
    PYTHON_EXEC="/path/to/your/katana-bot-project/venv/bin/python" # Or just python3 if in PATH
    SCRIPT_PATH="/path/to/your/katana_bot-project/tools/check_heartbeat.py"
    HEARTBEAT_FILE="/path/to/your/katana-bot-project/katana_heartbeat.txt"
    LOG_FILE="/var/log/katana_bot/heartbeat_check.log" # Ensure this dir exists and is writable

    # Run the check
    output=$($PYTHON_EXEC $SCRIPT_PATH --file $HEARTBEAT_FILE --threshold 300 2>&1)
    exit_code=$?

    echo "$(date): Check script exited with $exit_code. Output: $output" >> $LOG_FILE

    if [ $exit_code -ne 0 ]; then
        # Heartbeat failed, send alert
        alert_subject="Katana Bot Heartbeat FAILED"
        alert_body="Katana Bot heartbeat is stale or file is missing. Check logs.\nOutput:\n$output"

        # Example: Send email (requires `mailutils` or `sendmail` configured)
        # echo -e "$alert_body" | mail -s "$alert_subject" your_email@example.com

        # Example: Send Telegram message via another bot's API (replace with your bot token and chat ID)
        # TELEGRAM_BOT_TOKEN_ALERT="your_alert_bot_token"
        # TELEGRAM_CHAT_ID_ALERT="your_chat_id_for_alerts"
        # curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN_ALERT/sendMessage" \
        #     -d chat_id="$TELEGRAM_CHAT_ID_ALERT" \
        #     -d text="$alert_subject\n\n$alert_body" > /dev/null

        echo "ALERT: $alert_subject - $alert_body (Actual notification would be sent here)" >> $LOG_FILE
    fi
    ```
    Then, schedule `run_heartbeat_check_and_alert.sh` in cron instead of `check_heartbeat.py` directly.

*   **Option 2: Modify `check_heartbeat.py` Directly**
    1.  Add necessary Python libraries (e.g., `smtplib` for email, `requests` for generic HTTP APIs like Telegram) to your environment if they are not already standard.
    2.  Implement notification functions within `check_heartbeat.py` (e.g., `send_email_alert`, `send_telegram_alert`).
    3.  Call these functions from the `simulate_alert` function (perhaps renaming `simulate_alert` to `trigger_alert`).
    4.  Securely manage credentials for these notification services (e.g., via environment variables accessible to the cron job, or a separate, secured configuration file read by `check_heartbeat.py`).

    **Example: Sending Email with `smtplib` (conceptual snippet for `check_heartbeat.py`)**
    ```python
    # import smtplib
    # from email.mime.text import MIMEText

    # def send_email_alert(subject, body, to_email, from_email, smtp_server, smtp_port, smtp_user, smtp_pass):
    #     msg = MIMEText(body)
    #     msg['Subject'] = subject
    #     msg['From'] = from_email
    #     msg['To'] = to_email
    #     try:
    #         with smtplib.SMTP_SSL(smtp_server, smtp_port) as server: # Or SMTP for non-SSL
    #             server.login(smtp_user, smtp_pass)
    #             server.sendmail(from_email, [to_email], msg.as_string())
    #         print(f"Email alert sent to {to_email}", file=sys.stderr)
    #     except Exception as e:
    #         print(f"Failed to send email alert: {e}", file=sys.stderr)
    ```

    **Example: Sending Telegram Message with `requests` (conceptual snippet for `check_heartbeat.py`)**
    ```python
    # import requests
    # TELEGRAM_ALERT_BOT_TOKEN = os.getenv("TELEGRAM_ALERT_BOT_TOKEN")
    # TELEGRAM_ALERT_CHAT_ID = os.getenv("TELEGRAM_ALERT_CHAT_ID")

    # def send_telegram_alert(message_text):
    #     if not TELEGRAM_ALERT_BOT_TOKEN or not TELEGRAM_ALERT_CHAT_ID:
    #         print("CRITICAL: Telegram alert bot token or chat ID not configured.", file=sys.stderr)
    #         return
    #     url = f"https://api.telegram.org/bot{TELEGRAM_ALERT_BOT_TOKEN}/sendMessage"
    #     payload = {"chat_id": TELEGRAM_ALERT_CHAT_ID, "text": message_text, "parse_mode": "Markdown"}
    #     try:
    #         response = requests.post(url, data=payload, timeout=10)
    #         response.raise_for_status() # Raise an exception for HTTP error codes
    #         print(f"Telegram alert sent to chat ID {TELEGRAM_ALERT_CHAT_ID}", file=sys.stderr)
    #     except requests.exceptions.RequestException as e:
    #         print(f"Failed to send Telegram alert: {e}", file=sys.stderr)
    ```
    Remember to handle API keys and chat IDs securely, likely via environment variables set for the cron job.

### Future Monitoring Enhancements (Conceptual)

*   **HTTP `/health` Endpoint:**
    *   For more active checks by load balancers or external monitoring services, you could add a simple HTTP server (e.g., using Flask or http.server in a separate thread) to `katana_bot.py`.
    *   This server would expose an endpoint like `/health`.
    *   A request to `/health` could check:
        *   If the main bot polling thread/loop is considered active.
        *   The age of the last successful message processing (if tracked).
        *   Connection status to Telegram (if `telebot` provides such a check).
    *   It would return an HTTP 200 status if healthy, or 503 Service Unavailable if not.

*   **Prometheus Metrics:**
    *   Integrate a Prometheus client library (e.g., `prometheus_client`) into `katana_bot.py`.
    *   Expose metrics on an HTTP endpoint (often `/metrics`), such as:
        *   Number of messages processed.
        *   Number of errors (total, by type).
        *   NLP client request latencies.
        *   Information about the bot's state.
    *   Set up Prometheus to scrape this endpoint and Alertmanager to fire alerts based on these metrics.

## Troubleshooting Common Issues

*   **Bot does not start / `ValueError` for Token:**
    *   Ensure `KATANA_TELEGRAM_TOKEN` environment variable is correctly set *in the environment where the bot script runs*. This is crucial for systemd/supervisor services.
    *   Verify the token format is `numbers:characters`.
*   **`ModuleNotFoundError`:**
    *   If running as a service, ensure `WorkingDirectory` is correct and the Python executable used (especially if from a virtual environment) can find all installed packages.
    *   Activate the virtual environment if necessary before running, or use the full path to the venv Python interpreter in service files.
*   **Heartbeat file not updated / Permission errors:**
    *   Ensure the directory where `katana_heartbeat.txt` (project root by default) is located is writable by the user the bot service runs as.
    *   Check logs from `katana_bot.py` for any `IOError` related to heartbeat file writing.
*   **`check_heartbeat.py` script issues:**
    *   Verify paths to the script and heartbeat file are correct in cron jobs.
    *   Ensure the script has execute permissions (`chmod +x tools/check_heartbeat.py`).
    *   Check logs from the cron job (e.g., `/var/log/katana_bot/heartbeat_check.log` in the example) for errors.
*   **Service fails to stay running (systemd/supervisor):**
    *   Check `journalctl -u katana_bot.service` (for systemd) or Supervisor's log files for the bot process. These logs will contain startup errors or runtime exceptions from `katana_bot.py`.
    *   Ensure `RestartSec` (systemd) or `startsecs`/`startretries` (Supervisor) are configured to allow for recovery time if there are transient issues.
*   **Graceful Shutdown Issues**:
    *   If the bot doesn't shut down cleanly with `Ctrl+C` or service stop commands, check that the `signal` handlers in `katana_bot.py` are correctly registered and that `bot.stop_polling()` behaves as expected.
    *   Ensure the user running the bot process has permissions to receive and handle `SIGINT`/`SIGTERM`.

### Adapting Service Files for Different Environments

*   **Paths**: The most common change needed in `katana_bot.service` (systemd) and `katana_bot.conf` (Supervisor) will be the absolute paths in `WorkingDirectory`, `ExecStart` (for systemd), `command`, and `directory` (for Supervisor), and log file paths. Always use absolute paths for these in service configurations.
*   **Python Interpreter**: If you use a virtual environment (recommended), ensure `ExecStart`/`command` points to the Python interpreter *inside* the `venv` (e.g., `/path/to/project/venv/bin/python`). If using a system Python, ensure it's the correct version (`python3`).
*   **User/Group**: Change `User=your_user` and `Group=your_group` (systemd) or `user=your_user` (Supervisor) to a dedicated, non-root user with appropriate permissions for the project directory, log directories, and heartbeat file.
*   **Environment Variables**: The method of setting environment variables (directly in the service file, via `EnvironmentFile`, or through a wrapper script for Supervisor) should be chosen based on your security needs and server setup. `EnvironmentFile` is generally preferred for systemd when managing multiple secrets.
```
