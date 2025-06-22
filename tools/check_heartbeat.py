import os
import sys
import argparse
from datetime import datetime, timezone, timedelta

DEFAULT_HEARTBEAT_FILE_PATH = "/tmp/katana_bot_heartbeat.txt" # Should match .env default or be passed as arg
DEFAULT_MAX_AGE_SECONDS = 120  # Consider a heartbeat stale if older than 2 minutes

def main():
    parser = argparse.ArgumentParser(description="Check Katana Bot heartbeat file.")
    parser.add_argument(
        "--file-path",
        type=str,
        default=os.getenv('HEARTBEAT_FILE_PATH', DEFAULT_HEARTBEAT_FILE_PATH),
        help=f"Path to the heartbeat file. Defaults to env HEARTBEAT_FILE_PATH or '{DEFAULT_HEARTBEAT_FILE_PATH}'."
    )
    parser.add_argument(
        "--max-age",
        type=int,
        default=int(os.getenv('HEARTBEAT_MAX_AGE_SECONDS', DEFAULT_MAX_AGE_SECONDS)),
        help=f"Maximum age of the heartbeat file in seconds. Defaults to env HEARTBEAT_MAX_AGE_SECONDS or {DEFAULT_MAX_AGE_SECONDS}."
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output."
    )

    args = parser.parse_args()

    if args.verbose:
        print(f"Checking heartbeat file: {args.file_path}")
        print(f"Maximum allowed age: {args.max_age} seconds")

    if not os.path.exists(args.file_path):
        print(f"CRITICAL: Heartbeat file '{args.file_path}' does not exist.")
        sys.exit(2) # Nagios CRITICAL state

    try:
        with open(args.file_path, 'r') as f:
            heartbeat_timestamp_str = f.read().strip()

        heartbeat_dt = datetime.fromisoformat(heartbeat_timestamp_str)
    except Exception as e:
        print(f"CRITICAL: Could not read or parse heartbeat file '{args.file_path}': {e}")
        sys.exit(2)

    now_utc = datetime.now(timezone.utc)
    age_seconds = (now_utc - heartbeat_dt).total_seconds()

    if args.verbose:
        print(f"Heartbeat timestamp: {heartbeat_dt.isoformat()}")
        print(f"Current UTC time: {now_utc.isoformat()}")
        print(f"Heartbeat age: {age_seconds:.2f} seconds")

    if age_seconds < 0:
        print(f"WARNING: Heartbeat timestamp '{heartbeat_dt.isoformat()}' is in the future. Check system clocks.")
        sys.exit(1) # Nagios WARNING state

    if age_seconds > args.max_age:
        critical_message = f"CRITICAL: Katana Bot heartbeat is stale! Last update was {age_seconds:.2f} seconds ago (max allowed: {args.max_age}s)."
        print(critical_message)
        # --- Alerting Integration Placeholder ---
        # In a real scenario, trigger an alert here.
        # Example: send_telegram_alert(critical_message)
        #          send_email_alert("Katana Bot Alert", critical_message)
        # See function `send_telegram_alert` below for a conceptual example.
        # --------------------------------------
        sys.exit(2) # Nagios CRITICAL state

    ok_message = f"OK: Heartbeat is current. Last update was {age_seconds:.2f} seconds ago."
    if args.verbose: # Only print OK message if verbose, to keep cron logs clean on success
        print(ok_message)
    sys.exit(0) # Nagios OK state

def send_telegram_alert(message: str):
    """
    Conceptual function to send an alert message via a Telegram bot.
    Requires environment variables:
    - ALERT_TELEGRAM_BOT_TOKEN: Token for the bot that sends alerts.
    - ALERT_TELEGRAM_CHAT_ID: Chat ID to send the alert to.
    """
    bot_token = os.getenv('ALERT_TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('ALERT_TELEGRAM_CHAT_ID')

    if not bot_token or not chat_id:
        print("WARNING: Telegram alert variables (ALERT_TELEGRAM_BOT_TOKEN, ALERT_TELEGRAM_CHAT_ID) not set. Cannot send alert.")
        return

    # This is a simplified example. A real implementation would use a library like `requests` or `python-telegram-bot`.
    # import requests
    # url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    # payload = {"chat_id": chat_id, "text": message}
    # try:
    #     response = requests.post(url, data=payload, timeout=10)
    #     response.raise_for_status() # Raise an exception for HTTP errors
    #     print(f"Successfully sent Telegram alert to chat_id {chat_id}.")
    # except Exception as e:
    #     print(f"ERROR: Failed to send Telegram alert: {e}")
    print(f"CONCEPTUAL ALERT (Telegram): To ChatID {chat_id} - Message: {message}")


if __name__ == "__main__":
    main()
