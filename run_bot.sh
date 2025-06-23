#!/bin/bash

LOG_FILE="/Users/a1/katana/logs/run_bot_script.log"
MAX_RESTARTS=5
RESTART_COUNT=0

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

log_message "run_bot.sh script started."

# Ensure the main bot log directory exists, as the bot script might create it too
mkdir -p /Users/a1/katana/logs

# Activate virtual environment if you have one
# source /path/to/your/venv/bin/activate

while [ $RESTART_COUNT -lt $MAX_RESTARTS ]; do
    log_message "Starting bot.py (Attempt: $((RESTART_COUNT + 1)))..."
    # Ensure bot.py is executable or call it with python interpreter
    # Assuming bot.py is in the same directory as this script
    # And that TELEGRAM_API_TOKEN is set in the environment where this script runs or in bot.py
    python bot.py

    EXIT_CODE=$?
    log_message "bot.py exited with code $EXIT_CODE."

    if [ $EXIT_CODE -eq 0 ]; then
        log_message "Bot stopped gracefully. Exiting run_bot.sh."
        break # Exit loop if bot stopped intentionally (exit code 0)
    else
        log_message "Bot crashed or stopped unexpectedly. Restarting..."
        RESTART_COUNT=$((RESTART_COUNT + 1))
        sleep 5 # Wait for 5 seconds before restarting
    fi
done

if [ $RESTART_COUNT -ge $MAX_RESTARTS ]; then
    log_message "Maximum restart attempts reached ($MAX_RESTARTS). Not restarting anymore."
fi

log_message "run_bot.sh script finished."
