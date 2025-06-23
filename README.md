# Katana Telegram Bot

Katana is a Telegram bot designed for flexible interaction and command processing.

## Project Structure

-   `main.py`: Main entry point for the application, handles interface selection and core processing loop.
-   `bot/`: Contains supporting bot logic.
    -   `katana_bot.py`: Utility module for bot functions (e.g., heartbeat, specific handlers if any).
    -   `nlp_clients/`: Clients for interacting with NLP models (e.g., Anthropic, OpenAI).
    -   `commands/`: Directory where received JSON commands might be stored or processed (now managed from `main.py`).
-   `src/`: Source directory for modular components.
    -   `interfaces/`: Contains different communication interfaces.
        -   `interface_base.py`: Abstract base class for interfaces.
        -   `telegram_interface.py`: Telegram specific communication interface.
        -   `gemma_interface.py`: Interface for connecting to the Gemma/Kodjima API.
        -   `tests/`: Unit tests for the interfaces.
-   `ui/`: Contains the source code for a potential web UI (details might vary).
-   `legacy_ui/`: Contains source code for a previous web UI.
-   `requirements.txt`: Python dependencies.
-   `.env.example`: Example file for environment variable configuration.

## Running Locally

To run the Katana bot on your local machine, follow these steps:

### 1. Prerequisites

-   Python 3.8+
-   pip (Python package installer)

### 2. Setup Environment Variables

The bot requires certain API keys and tokens to be set as environment variables.

1.  Copy the example environment file:
    ```bash
    cp .env.example .env
    ```
2.  Edit the `.env` file and fill in your actual credentials:

    ```env
    # --- Core Interface Selection ---
    # INTERFACE: Determines the communication mode.
    # Options: "telegram" (default), "gemma"
    # - "telegram": Runs the bot as a Telegram bot.
    # - "gemma":    Runs the application to send a single request to the Gemma/Kodjima API.
    #               Requires GEMMA_API_KEY and optionally GEMMA_PAYLOAD_JSON.
    INTERFACE="telegram"

    # --- Telegram Interface Configuration ---
    KATANA_TELEGRAM_TOKEN="YOUR_TELEGRAM_BOT_TOKEN" # Get this from BotFather on Telegram

    # --- Gemma Interface Configuration ---
    # GEMMA_API_KEY: Your API key for the Gemma/Kodjima service.
    # Required if INTERFACE is "gemma".
    GEMMA_API_KEY="YOUR_GEMMA_API_KEY"

    # GEMMA_PAYLOAD_JSON: Optional JSON string payload for a single run with INTERFACE="gemma".
    # If not provided, a default test payload is used by main.py.
    # Example: GEMMA_PAYLOAD_JSON='{"text": "Translate this to French: Hello", "user_id": "gemma_cli_user"}'
    # GEMMA_PAYLOAD_JSON='{"text": "Your query here"}'


    # --- Optional NLP Service Keys (used by core processing logic) ---
    ANTHROPIC_API_KEY="YOUR_ANTHROPIC_API_KEY"     # Optional: if you use Anthropic models
    OPENAI_API_KEY="YOUR_OPENAI_API_KEY"         # Optional: if you use OpenAI models
    ```

    -   `INTERFACE`: Chooses the active communication channel.
        -   If `telegram`, `KATANA_TELEGRAM_TOKEN` is essential.
        -   If `gemma`, `GEMMA_API_KEY` is essential. `GEMMA_PAYLOAD_JSON` can be used to provide the input query.
    -   `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` are needed if the bot's core logic (`process_user_message` -> `get_katana_response_async`) is configured to use these specific NLP services.

### 3. Install Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

### 4. Run the Bot

Execute the main application script:

```bash
python main.py
```

The behavior of the application will depend on the `INTERFACE` environment variable:

-   **If `INTERFACE="telegram"` (default):**
    You should see log messages indicating the Telegram bot is starting.
-   **If `INTERFACE="gemma"`:**
    The application will perform a single execution. It will use the `GEMMA_API_KEY` to send a request to the Gemma/Kodjima API. The payload for this request is taken from the `GEMMA_PAYLOAD_JSON` environment variable, or a default test payload if not set. Output from this mode (including any response from the Gemma/Kodjima API) will be logged to the console.

### 5. Running with Gemma Interface (Single Shot)

If you want to test or use the Gemma/Kodjima API integration directly:

1.  Set your environment variables in the `.env` file:
    ```env
    INTERFACE="gemma"
    GEMMA_API_KEY="YOUR_ACTUAL_GEMMA_API_KEY"
    # Optionally, provide the JSON payload for the query:
    GEMMA_PAYLOAD_JSON='{"text": "What is the weather like in Tokyo?", "user_id": "example_user_01"}'
    ```
    Refer to `main.py` for the structure of `GEMMA_PAYLOAD_JSON` that `process_user_message` expects (it should at least contain a "text" field).

2.  Run `main.py`:
    ```bash
    python main.py
    ```
    The application will:
    - Initialize the `GemmaInterface`.
    - The `process_user_message` function in `main.py` will prepare a request dictionary based on the `GEMMA_PAYLOAD_JSON` (or default).
    - The `GemmaInterface.send()` method will then POST this request dictionary to the configured Gemma/Kodjima API endpoint (`https://api.kodjima.com/v1/query` by default).
    - Logs related to this operation, including the status of the API call, will be printed to the console. Note that the current `GemmaInterface.send()` does not directly return the API's response content to the main loop for display, but it logs the attempt and status.

You should see log messages in your console indicating the application is starting and processing based on the selected interface.

### 5. Verify Bot is Alive

-   Open your Telegram client.
-   Find your bot (the one associated with `KATANA_TELEGRAM_TOKEN`).
-   Send it a `/start` command or any text message.
-   Check your console logs. You should see the incoming message logged and the bot's response. The bot should reply to you in Telegram.

## Bot Stability Features

The current version of the bot includes several features to improve its stability:

-   **Continuous Polling**: `bot.polling(none_stop=True)` is used to ensure the bot keeps running even if there are minor errors during message handling or network issues with Telegram.
-   **Global Error Handling**: The main message handler has a `try-except` block to catch unexpected exceptions. These errors are logged with a full stack trace, but the bot process itself will not crash.
-   **Environment Variable Logging**: On startup, the bot logs whether critical environment variables (like API tokens) have been successfully loaded or are missing.
-   **Response Logging**: Each reply sent by the bot to a user is logged, which aids in debugging.

## Recommendations for Auto-запуска and Перезапуска (Production/Staging)

For running the bot in a more persistent manner (e.g., on a server), it's recommended to use a process manager. This will handle automatically restarting the bot if it ever crashes unexpectedly (despite the `none_stop=True` and `try-except` measures) or after a server reboot.

### systemd (Linux)

A robust way to manage the Katana bot on a Linux server is by using `systemd`. This ensures the bot automatically starts on boot and restarts if it unexpectedly fails.

1.  **Prepare your Environment:**
    *   Ensure your bot project (including `main.py`, `requirements.txt`, and your `.env` file) is deployed to a stable directory on your server, for example, `/opt/katana-bot`.
    *   It's recommended to run the bot under a dedicated user account with limited privileges.
        ```bash
        # Example: Create a user 'katana_bot_user'
        sudo useradd -r -s /bin/false katana_bot_user
        sudo chown -R katana_bot_user:katana_bot_user /opt/katana-bot
        ```
    *   Make sure Python 3 and `pip` are installed system-wide or in a virtual environment accessible by the service. If using a virtual environment, the `ExecStart` path in the service file must point to the Python executable within that venv.

2.  **Copy the Service File:**
    *   A template systemd service file is provided in `deploy/systemd/katana-bot.service`. Copy this file to your systemd directory:
        ```bash
        sudo cp deploy/systemd/katana-bot.service /etc/systemd/system/katana-bot.service
        ```

3.  **Customize the Service File:**
    *   Open `/etc/systemd/system/katana-bot.service` with a text editor (e.g., `sudo nano` or `sudo vim`).
    *   **Crucially, update the following placeholders:**
        *   `Documentation`: (Optional) Correct the path to your README.
        *   `User` and `Group`: Uncomment and set to the dedicated user you created (e.g., `katana_bot_user`). If you didn't create a specific user, you can run it as another user, but a dedicated one is safer.
        *   `WorkingDirectory`: Set this to the absolute path where your bot project is located (e.g., `/opt/katana-bot`).
        *   `EnvironmentFile`: Set this to the absolute path of your `.env` file (e.g., `/opt/katana-bot/.env`).
        *   `ExecStart`: Ensure this points to your Python 3 executable and the absolute path to `main.py` within your project (e.g., `/usr/bin/python3 /opt/katana-bot/main.py` or `/opt/katana-bot/venv/bin/python /opt/katana-bot/main.py` if using a venv).
    *   Review other settings like `RestartSec` as needed. The default logging is to `journald`.

4.  **Reload systemd, Enable, and Start the Service:**
    *   After saving your changes to the service file, tell systemd to reload its configuration:
        ```bash
        sudo systemctl daemon-reload
        ```
    *   Enable the service to start automatically on boot:
        ```bash
        sudo systemctl enable katana-bot.service
        ```
    *   Start the service immediately:
        ```bash
        sudo systemctl start katana-bot.service
        ```

5.  **Check Service Status and Logs:**
    *   Verify that the service is running:
        ```bash
        sudo systemctl status katana-bot.service
        ```
        You should see output indicating it's "active (running)".
    *   View the bot's logs (if `StandardOutput=journal` and `StandardError=journal` are used):
        ```bash
        sudo journalctl -u katana-bot.service -f
        ```
        The `-f` flag follows the log output in real-time. Press `Ctrl+C` to exit.
        If you have configured file logging (see "File-based Logging" section below), logs will also be available in the specified file.

6.  **Stopping or Restarting the Service:**
    *   To stop the service:
        ```bash
        sudo systemctl stop katana-bot.service
        ```
    *   To restart the service (e.g., after updating the bot's code or `.env` file):
        ```bash
        sudo systemctl restart katana-bot.service
        ```

## File-based Logging and Rotation

By default, the bot logs to the console. You can also configure it to log to a file, which is recommended for production deployments managed by systemd or Supervisor.

### Enabling File Logging

1.  **Set Environment Variables:**
    Define the following environment variables in your `.env` file:
    ```env
    # .env
    LOG_LEVEL="INFO"  # Or DEBUG, WARNING, ERROR, CRITICAL
    LOG_FILE_PATH="/var/log/katana-bot/katana-bot.log" # Choose your desired path
    ```
    *   `LOG_LEVEL`: Controls the verbosity of logs (both console and file).
    *   `LOG_FILE_PATH`: Specifies the absolute path to the log file. If this variable is not set or is empty, file logging will be disabled.

2.  **Ensure Directory and Permissions:**
    The directory for the log file must exist, and the user running the bot must have write permissions to it.
    For the example path `/var/log/katana-bot/katana-bot.log`:
    ```bash
    sudo mkdir -p /var/log/katana-bot
    sudo chown katana_bot_user:katana_bot_user /var/log/katana-bot # Replace katana_bot_user with your bot's user
    sudo chmod 755 /var/log/katana-bot
    # The log file itself will be created by the application.
    ```

When `main.py` starts, its logging setup (currently `logging.basicConfig`) will determine how logs are handled. For file logging based on `LOG_FILE_PATH` to work as described, `main.py` would need to be enhanced to explicitly add a `FileHandler` if `LOG_FILE_PATH` is set (similar to how `run_bot_locally.py` previously handled it). This documentation assumes such setup is or will be in `main.py`.

### Log Rotation with `logrotate`

To prevent log files from growing indefinitely, you should set up log rotation. On Linux systems, `logrotate` is the standard tool.

1.  **Create `logrotate` Configuration:**
    A sample `logrotate` configuration file is provided at `deploy/logrotate/katana-bot`. This file should be copied or linked into your system's `logrotate` configuration directory.
    ```bash
    sudo cp deploy/logrotate/katana-bot /etc/logrotate.d/katana-bot
    ```

2.  **Customize the Configuration:**
    Open `/etc/logrotate.d/katana-bot` and adjust it to your needs:
    *   Verify the path to your log file matches `LOG_FILE_PATH`.
    *   Adjust `rotate` (number of old logs to keep), `daily`/`weekly`/`monthly`, and compression options.
    *   **Crucially, ensure the `create` directive specifies the correct user and group** that the bot runs as, so the new log file has the correct permissions. For example: `create 0640 katana_bot_user adm`.

3.  **Test `logrotate` (Optional):**
    You can test your `logrotate` configuration:
    ```bash
    sudo logrotate /etc/logrotate.conf --debug
    # To force rotation for a specific config (be careful with this on production):
    # sudo logrotate --force /etc/logrotate.d/katana-bot
    ```
    `logrotate` is typically run automatically by a cron job (e.g., `/etc/cron.daily/logrotate`).

This setup ensures that your bot's logs are managed efficiently, preventing them from consuming excessive disk space.

## Liveness Monitoring (Heartbeat File)

To monitor if the bot is actively running and processing, a heartbeat mechanism is implemented. The bot periodically writes the current timestamp to a specified file. An external script can then check this file's freshness.

### How it Works

1.  **Bot-side:**
    *   If `HEARTBEAT_FILE_PATH` is set in the `.env` file, the bot starts a background thread.
    *   This thread updates the content of `HEARTBEAT_FILE_PATH` with the current UTC timestamp at an interval defined by `HEARTBEAT_INTERVAL_SECONDS` (default 30 seconds).
2.  **Monitoring-side:**
    *   The `tools/check_heartbeat.py` script can be run (e.g., by a cron job) to check the heartbeat file.
    *   It reads the timestamp from the file and compares it to the current time.
    *   If the file is missing, unreadable, or the timestamp is older than `HEARTBEAT_MAX_AGE_SECONDS` (default 120 seconds), the script exits with a non-zero status code (CRITICAL or WARNING), indicating a problem.
    *   Otherwise, it exits with a zero status code (OK).

### Setup

1.  **Configure Environment Variables:**
    Add these variables to your `.env` file:
    ```env
    # .env
    HEARTBEAT_FILE_PATH="/var/run/katana-bot/heartbeat.txt"  # Or /tmp/katana_bot_heartbeat.txt
    HEARTBEAT_INTERVAL_SECONDS="30"                         # Bot updates file every 30s
    HEARTBEAT_MAX_AGE_SECONDS="120"                         # Monitor script flags error if older than 120s
    ```
    *   Choose a `HEARTBEAT_FILE_PATH` where the bot user has write permissions. Common locations are `/tmp/` or `/var/run/your_bot_name/`.
        ```bash
        # Example for /var/run/katana-bot/
        sudo mkdir -p /var/run/katana-bot
        sudo chown katana_bot_user:katana_bot_user /var/run/katana-bot # Use your bot's user
        sudo chmod 775 /var/run/katana-bot # Ensure user can write
        ```
    *   `HEARTBEAT_MAX_AGE_SECONDS` should be greater than `HEARTBEAT_INTERVAL_SECONDS` (e.g., 2-4 times the interval) to allow for minor delays.

2.  **Schedule `check_heartbeat.py`:**
    Use a cron job to run `tools/check_heartbeat.py` periodically (e.g., every minute or every 5 minutes).
    Open your crontab for editing (e.g., `crontab -e` for the current user, or edit system cron files):
    ```cron
    # Example: Run check_heartbeat.py every 5 minutes
    # Make sure to use absolute paths and the correct python interpreter
    # Adjust file paths and user for `su` if running as root but checking a file owned by another user.
    */5 * * * * /usr/bin/python3 /path/to/your/katana-bot-project/tools/check_heartbeat.py --file-path /var/run/katana-bot/heartbeat.txt --max-age 120 >> /var/log/katana-bot/heartbeat_check.log 2>&1
    ```
    *   The command passes `--file-path` and `--max-age` explicitly, but these can also be controlled by setting `HEARTBEAT_FILE_PATH` and `HEARTBEAT_MAX_AGE_SECONDS` in the environment where the cron job runs.
    *   The output (OK, CRITICAL, WARNING) and exit code of `check_heartbeat.py` can be used by monitoring systems (like Nagios, Zabbix, or custom alerting scripts) to trigger notifications if the bot appears to be down.

3.  **Alerting (Conceptual):**
    The `check_heartbeat.py` script currently prints CRITICAL/WARNING messages to standard output. To get actual alerts:
    *   Modify `check_heartbeat.py` to include logic for sending an email, a Telegram message, or calling another alerting API when a CRITICAL state is detected.
    *   Or, use a monitoring system that can interpret the script's exit codes and output to manage alerts.

This heartbeat mechanism provides a simple yet effective way to monitor the bot's liveness.
    For actual alert notifications, the `send_telegram_alert` function (or a similar custom function for email/other services) in `tools/check_heartbeat.py` needs to be implemented and configured with necessary API tokens and recipient details (e.g., via `ALERT_TELEGRAM_BOT_TOKEN` and `ALERT_TELEGRAM_CHAT_ID` environment variables).

## Deployment Guide

For a comprehensive, step-by-step guide to deploying the bot on a new server, including environment setup, configuration, and service management, please refer to the [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) file.

## Graceful Shutdown

The bot includes mechanisms for a basic graceful shutdown:
- When the application is stopped (e.g., via `Ctrl+C` or `systemctl stop`), `main.py` attempts to cancel running asyncio tasks. If the heartbeat functionality from `bot/katana_bot.py` is used and integrated into `main.py`'s lifecycle, it should also be stopped gracefully.
- **Further Considerations**: True graceful shutdown of active message handlers (ensuring they complete processing before exit) can be complex, especially with polling-based interfaces. The current `TelegramInterface` uses a separate thread for polling, and `main.py`'s shutdown sequence attempts to cancel tasks in its main asyncio loop.

### Supervisor

1.  Install Supervisor: `sudo apt-get install supervisor` (or equivalent for your OS).
2.  Create a configuration file for the bot, e.g., `/etc/supervisor/conf.d/katana-bot.conf`:

    ```ini
    [program:katana-bot]
    command=/usr/bin/python /path/to/your/katana-bot-project/main.py ; Full command
    directory=/path/to/your/katana-bot-project/ ; Project directory
    autostart=true
    autorestart=true
    stderr_logfile=/var/log/katana-bot.err.log
    stdout_logfile=/var/log/katana-bot.out.log
    user=your_username ; User to run as
    environment=PYTHONUNBUFFERED=1 # Ensures logs are written immediately
    # You might need to ensure .env variables are loaded,
    # either by sourcing them in the command or ensuring supervisor user has them.
    # Alternatively, have main.py load them via python-dotenv, which it does.
    ```
    Ensure the paths and username are correct. The `python-dotenv` library used in `main.py` should handle loading variables from the `.env` file in the specified `directory`.

3.  Tell Supervisor to read the new config:
    ```bash
    sudo supervisorctl reread
    sudo supervisorctl update
    ```
4.  Start the bot process:
    ```bash
    sudo supervisorctl start katana-bot
    ```
5.  Check status:
    ```bash
    sudo supervisorctl status katana-bot
    ```

Choose the method that best fits your deployment environment. Both systemd and Supervisor are robust options.

## CI/CD (Continuous Integration / Continuous Deployment)

A basic CI workflow is set up using GitHub Actions. You can find the configuration in `.github/workflows/ci.yml`.

### Current CI Setup

-   **Trigger**: The workflow runs on pushes and pull requests to the `dev` and `main` branches.
-   **Jobs**:
    1.  `lint-and-test`:
        *   Checks out the code.
        *   Sets up multiple Python versions (e.g., 3.9, 3.10, 3.11) to test compatibility.
        *   Installs dependencies from `requirements.txt`.
        *   **Lints**: Runs `flake8` to check for code style issues and potential errors.
        *   **Tests**: Runs `pytest` to execute automated tests. (Assumes tests are located in standard pytest-discoverable locations like `bot/tests/`).

### Extending CI/CD

This is a foundational CI setup. You can extend it by:

-   **Adding more tests**: Increase test coverage for more robust validation.
-   **Building artifacts**: If you need to package the bot (e.g., into a Docker container or a Python wheel), add a build job.
-   **Deployment (CD)**: Add jobs to automatically deploy the bot to staging or production environments after successful tests and builds on specific branches (e.g., `main`). This would typically involve:
    *   Building a Docker image and pushing it to a registry.
    *   Or, copying files to a server and restarting the systemd/supervisor service.
    *   Using GitHub secrets to store deployment credentials securely.
-   **Notifications**: Configure notifications (e.g., Slack, email) for build successes or failures.

The `ci.yml` file includes commented-out placeholders for a build job as an example starting point.

---

Happy botting with Katana! ⚔️
```
