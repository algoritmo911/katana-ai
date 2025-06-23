import os
import telegram
import argparse

def send_telegram_message(message, token, chat_id):
    """Sends a message to a Telegram chat."""
    try:
        bot = telegram.Bot(token=token)
        bot.send_message(chat_id=chat_id, text=message, parse_mode=telegram.ParseMode.MARKDOWN)
        print("Telegram notification sent successfully.")
    except Exception as e:
        print(f"Error sending Telegram notification: {e}")

def format_success_message():
    """Formats the success message."""
    return "✅ Deploy прошёл успешно"

def format_deploy_failure_message(error_log_path="error.log"):
    """Formats the deployment failure message."""
    message = "❌ Deploy упал"
    if os.path.exists(error_log_path):
        try:
            with open(error_log_path, 'r') as f:
                error_content = f.read().strip()
            if error_content:
                message += f", ошибки:\n```\n{error_content}\n```"
            else:
                message += ", `error.log` пуст."
        except Exception as e:
            message += f", не удалось прочитать `error.log`: {e}"
    else:
        message += ", `error.log` не найден."
    return message

def format_ci_failure_message(failed_tests_output):
    """Formats the CI failure message."""
    return f"🔧 CI упал: \n```\n{failed_tests_output}\n```"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send Telegram notifications.")
    parser.add_argument("message_type", choices=["success", "deploy_fail", "ci_fail"], help="Type of message to send.")
    parser.add_argument("--error_log", default="error.log", help="Path to the error log file for deploy_fail.")
    parser.add_argument("--failed_tests", default="No failed tests provided.", help="String detailing failed CI tests for ci_fail.")

    args = parser.parse_args()

    token = os.environ.get("BOT_NOTIFY_TOKEN")
    chat_id = os.environ.get("NOTIFY_CHAT_ID")

    if not token or not chat_id:
        print("Error: BOT_NOTIFY_TOKEN or NOTIFY_CHAT_ID environment variables not set.")
        exit(1)

    if args.message_type == "success":
        message = format_success_message()
    elif args.message_type == "deploy_fail":
        message = format_deploy_failure_message(args.error_log)
    elif args.message_type == "ci_fail":
        message = format_ci_failure_message(args.failed_tests)
    else:
        print(f"Unknown message type: {args.message_type}")
        exit(1)

    send_telegram_message(message, token, chat_id)
