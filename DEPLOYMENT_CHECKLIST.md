# Katana Bot Deployment Checklist

This checklist provides a step-by-step guide for deploying the Katana Telegram Bot to a new Linux server environment.

## 1. Server Preparation

*   [ ] **Access & Permissions**: Ensure you have SSH access to the server with `sudo` privileges.
*   [ ] **Python Installation**:
    *   [ ] Verify Python 3.8+ is installed. (e.g., `python3 --version`).
    *   [ ] Install `pip` for Python 3 if not present (e.g., `sudo apt update && sudo apt install python3-pip`).
    *   [ ] Install `python3-venv` for creating virtual environments (e.g., `sudo apt install python3-venv`).
*   [ ] **Dedicated User (Recommended)**:
    *   [ ] Create a non-root user to run the bot (e.g., `katana_bot_user`):
        ```bash
        sudo useradd -r -m -s /bin/bash katana_bot_user
        # -m creates home directory, -s /bin/bash allows login if needed for setup
        # For a service-only user, /bin/false is also an option after setup.
        ```
    *   This checklist assumes commands are run as your admin user, and `sudo` is used where necessary. Service will run as `katana_bot_user`.

## 2. Application Setup

*   [ ] **Clone Repository**:
    *   [ ] Clone the project into a suitable directory (e.g., `/opt/katana-bot`):
        ```bash
        sudo git clone <your_repository_url> /opt/katana-bot
        ```
    *   [ ] Navigate to the project directory: `cd /opt/katana-bot`
*   [ ] **Set Ownership**:
    *   [ ] Change ownership of the project directory to the dedicated user:
        ```bash
        sudo chown -R katana_bot_user:katana_bot_user /opt/katana-bot
        ```
*   [ ] **Switch to Dedicated User (for venv setup)**:
    *   `sudo -u katana_bot_user -i` (or `su - katana_bot_user`)
    *   `cd /opt/katana-bot`
*   [ ] **Create Virtual Environment**:
    *   [ ] `python3 -m venv venv`
*   [ ] **Activate Virtual Environment**:
    *   [ ] `source venv/bin/activate`
*   [ ] **Install Dependencies**:
    *   [ ] `pip install -r requirements.txt`
*   [ ] **Deactivate venv and return to admin user**:
    *   `deactivate`
    *   `exit` (if you switched user with `su -` or `sudo -u ... -i`)

## 3. Configuration (`.env` file)

*   [ ] **Create `.env` file**:
    *   [ ] `sudo cp /opt/katana-bot/.env.example /opt/katana-bot/.env`
*   [ ] **Edit `.env` file** (`sudo nano /opt/katana-bot/.env` or `sudo vim ...`):
    *   [ ] `KATANA_TELEGRAM_TOKEN`: Set your actual Telegram Bot token.
    *   [ ] `ANTHROPIC_API_KEY` (Optional): Set if using Anthropic.
    *   [ ] `OPENAI_API_KEY` (Optional): Set if using OpenAI.
    *   [ ] `LOG_LEVEL`: Set desired log level (e.g., `INFO`, `DEBUG`).
    *   [ ] `LOG_FILE_PATH`: Set absolute path for file logging (e.g., `/var/log/katana-bot/katana-bot.log`).
    *   [ ] `HEARTBEAT_FILE_PATH`: Set absolute path for the heartbeat file (e.g., `/var/run/katana-bot/heartbeat.txt`).
    *   [ ] `HEARTBEAT_INTERVAL_SECONDS`: (Default: 30)
    *   [ ] `HEARTBEAT_MAX_AGE_SECONDS`: (Default: 120)
*   [ ] **Set `.env` file ownership and permissions**:
    *   [ ] `sudo chown katana_bot_user:katana_bot_user /opt/katana-bot/.env`
    *   [ ] `sudo chmod 600 /opt/katana-bot/.env` (Restrict access to owner only)

## 4. Log Directory Setup

*   [ ] **Create Log Directory** (if `LOG_FILE_PATH` is configured):
    *   Example, if `LOG_FILE_PATH="/var/log/katana-bot/katana-bot.log"`:
        ```bash
        sudo mkdir -p /var/log/katana-bot
        sudo chown katana_bot_user:katana_bot_user /var/log/katana-bot
        sudo chmod 750 /var/log/katana-bot # User can write, group can read (e.g. adm for logrotate)
        ```

## 5. Heartbeat Directory Setup

*   [ ] **Create Heartbeat Directory** (if `HEARTBEAT_FILE_PATH` is configured):
    *   Example, if `HEARTBEAT_FILE_PATH="/var/run/katana-bot/heartbeat.txt"`:
        ```bash
        sudo mkdir -p /var/run/katana-bot
        sudo chown katana_bot_user:katana_bot_user /var/run/katana-bot
        sudo chmod 775 /var/run/katana-bot # User needs to write here
        ```
    *   Note: `/var/run` is often temporary (cleared on reboot). For persistence across reboots if needed (though heartbeat implies liveness of current process), consider another location or ensure systemd `tmpfiles.d` configuration. For a simple heartbeat, `/var/run` or `/tmp` is common.

## 6. Systemd Service Setup

*   [ ] **Copy Service File**:
    *   [ ] `sudo cp /opt/katana-bot/deploy/systemd/katana-bot.service /etc/systemd/system/katana-bot.service`
*   [ ] **Edit Service File** (`sudo nano /etc/systemd/system/katana-bot.service`):
    *   [ ] Update `User` and `Group` to `katana_bot_user` (or your chosen user).
    *   [ ] Update `WorkingDirectory` to `/opt/katana-bot`.
    *   [ ] Update `EnvironmentFile` to `/opt/katana-bot/.env`.
    *   [ ] Update `ExecStart` to `/opt/katana-bot/venv/bin/python /opt/katana-bot/run_bot_locally.py` (ensure Python path is from the venv).
    *   [ ] (Optional) Update `Documentation` path.
*   [ ] **Reload Systemd**:
    *   [ ] `sudo systemctl daemon-reload`
*   [ ] **Enable Service** (to start on boot):
    *   [ ] `sudo systemctl enable katana-bot.service`
*   [ ] **Start Service**:
    *   [ ] `sudo systemctl start katana-bot.service`
*   [ ] **Check Service Status**:
    *   [ ] `sudo systemctl status katana-bot.service` (Should show "active (running)")
    *   [ ] `journalctl -u katana-bot.service -f` (Check for startup logs and any errors)

## 7. Logrotate Setup

*   [ ] **Copy Logrotate Configuration**:
    *   [ ] `sudo cp /opt/katana-bot/deploy/logrotate/katana-bot /etc/logrotate.d/katana-bot`
*   [ ] **Edit Logrotate Configuration** (`sudo nano /etc/logrotate.d/katana-bot`):
    *   [ ] Verify the log file path matches `LOG_FILE_PATH` from `.env`.
    *   [ ] Ensure `create` directive uses the correct user/group (e.g., `create 0640 katana_bot_user adm` or `create 0640 katana_bot_user katana_bot_user`).
*   [ ] **Test Logrotate Configuration**:
    *   [ ] `sudo logrotate /etc/logrotate.conf --debug`
    *   [ ] (Optional, force rotation for testing) `sudo logrotate --force /etc/logrotate.d/katana-bot`
    *   Check that a new log file is created with correct permissions and old one is rotated/compressed.

## 8. Heartbeat Monitoring Setup (Cron)

*   [ ] **Edit Crontab** (for the root user, or a dedicated monitoring user):
    *   [ ] `sudo crontab -e`
    *   Add a line to run `check_heartbeat.py` (adjust paths and frequency):
        ```cron
        */5 * * * * /opt/katana-bot/venv/bin/python /opt/katana-bot/tools/check_heartbeat.py --file-path /var/run/katana-bot/heartbeat.txt --max-age 120 >> /var/log/katana-bot/heartbeat_check.log 2>&1
        ```
    *   Ensure the Python path in cron is correct (points to venv python).
*   [ ] **Verify Cron Job**:
    *   [ ] After the cron interval, check `/var/log/katana-bot/heartbeat_check.log` for output.
    *   [ ] Check that the heartbeat file (`/var/run/katana-bot/heartbeat.txt`) is being updated by the bot.

## 9. Final Verification

*   [ ] **Bot Functionality**:
    *   [ ] Send a message (e.g., `/start`) to your Telegram bot.
    *   [ ] Verify the bot responds as expected.
*   [ ] **Logging**:
    *   [ ] Check application logs (`LOG_FILE_PATH` or `journalctl`) for normal activity and any errors.
*   [ ] **Heartbeat**:
    *   [ ] Ensure the heartbeat file specified in `HEARTBEAT_FILE_PATH` is being updated regularly by the bot.
    *   [ ] Ensure the `check_heartbeat.py` cron job is running and reporting "OK".
*   [ ] **(Optional) Simulate Failure**:
    *   [ ] Stop the `katana-bot` service (`sudo systemctl stop katana-bot`).
    *   [ ] Wait for `check_heartbeat.py` to run via cron (or run manually). Verify it reports CRITICAL.
    *   [ ] Check if systemd attempts to restart the service (if it was an unexpected stop).
    *   [ ] Start the service again (`sudo systemctl start katana-bot`).

---
This checklist should help ensure a smooth and consistent deployment. Adjust paths and user names as per your specific setup.
```
