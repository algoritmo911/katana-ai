# Katana Telegram Bot

Katana is a Telegram bot designed for flexible interaction and command processing.

## Project Structure

-   `bot/`: Contains the core bot logic.
    -   `katana_bot.py`: Main entry point and message handling for the bot.
    -   `nlp_clients/`: Clients for interacting with NLP models (e.g., Anthropic, OpenAI).
    -   `commands/`: Directory where received JSON commands might be stored or processed.
-   `ui/`: Contains the source code for a potential web UI (details might vary).
-   `legacy_ui/`: Contains source code for a previous web UI.
-   `requirements.txt`: Python dependencies.
-   `run_bot_locally.py`: Script to run the bot locally.
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
    KATANA_TELEGRAM_TOKEN="YOUR_TELEGRAM_BOT_TOKEN" # Get this from BotFather on Telegram
    ANTHROPIC_API_KEY="YOUR_ANTHROPIC_API_KEY"     # Optional: if you use Anthropic models
    OPENAI_API_KEY="YOUR_OPENAI_API_KEY"         # Optional: if you use OpenAI models
    ```

    -   `KATANA_TELEGRAM_TOKEN`: This is essential for the bot to connect to Telegram.
    -   `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` are needed if the bot is configured to use these NLP services. If not used, the bot will log a warning but should still run with placeholder/stub responses.

### 3. Install Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

### 4. Run the Bot

Execute the local runner script:

```bash
python run_bot_locally.py
```

You should see log messages in your console indicating that the bot is starting and has successfully loaded the environment variables.

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

1.  Create a systemd service file, for example, `/etc/systemd/system/katana-bot.service`:

    ```ini
    [Unit]
    Description=Katana Telegram Bot
    After=network.target

    [Service]
    User=your_username             # Replace with the user you want to run the bot as
    Group=your_groupname           # Replace with the group for that user
    WorkingDirectory=/path/to/your/katana-bot-project # Replace with the actual path to the project
    EnvironmentFile=/path/to/your/katana-bot-project/.env # Path to your .env file
    ExecStart=/usr/bin/python /path/to/your/katana-bot-project/run_bot_locally.py # Replace with python path and script path
    Restart=always
    RestartSec=5s
    StandardOutput=journal
    StandardError=journal
    SyslogIdentifier=katana-bot

    [Install]
    WantedBy=multi-user.target
    ```

2.  Replace placeholders like `your_username`, `your_groupname`, and paths to your project and Python interpreter.
3.  Reload systemd: `sudo systemctl daemon-reload`
4.  Enable the service to start on boot: `sudo systemctl enable katana-bot.service`
5.  Start the service: `sudo systemctl start katana-bot.service`
6.  Check status: `sudo systemctl status katana-bot.service`
7.  View logs: `sudo journalctl -u katana-bot -f`

### Supervisor

1.  Install Supervisor: `sudo apt-get install supervisor` (or equivalent for your OS).
2.  Create a configuration file for the bot, e.g., `/etc/supervisor/conf.d/katana-bot.conf`:

    ```ini
    [program:katana-bot]
    command=/usr/bin/python /path/to/your/katana-bot-project/run_bot_locally.py ; Full command
    directory=/path/to/your/katana-bot-project/ ; Project directory
    autostart=true
    autorestart=true
    stderr_logfile=/var/log/katana-bot.err.log
    stdout_logfile=/var/log/katana-bot.out.log
    user=your_username ; User to run as
    environment=PYTHONUNBUFFERED=1 # Ensures logs are written immediately
    # You might need to ensure .env variables are loaded,
    # either by sourcing them in the command or ensuring supervisor user has them.
    # Alternatively, have run_bot_locally.py load them via python-dotenv, which it does.
    ```
    Ensure the paths and username are correct. The `python-dotenv` library used in `run_bot_locally.py` should handle loading variables from the `.env` file in the specified `directory`.

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
---

Happy botting with Katana! ⚔️
```
