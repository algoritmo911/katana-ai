import telebot
import json
import os
from pathlib import Path
from datetime import datetime
import subprocess # Added for run_katana_command
from nlp.main import process_message # <-- Import the new NLP engine

# TODO: Get API token from environment variable or secrets manager
# Using a format-valid dummy token for testing purposes if no env var is set.
API_TOKEN = os.environ.get('TELEGRAM_API_TOKEN', '12345:dummytoken')

bot = telebot.TeleBot(API_TOKEN)

# --- Logging Setup ---
LOG_DIR = Path('logs')
LOG_DIR.mkdir(parents=True, exist_ok=True)
TELEGRAM_LOG_FILE = LOG_DIR / 'telegram.log'

def log_to_file(message, filename=TELEGRAM_LOG_FILE):
    """Appends a message to the specified log file."""
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.utcnow().isoformat()} | {message}\n")

def log_local_bot_event(message):
    """Logs an event to the console and to the telegram.log file."""
    print(f"[BOT EVENT] {datetime.utcnow().isoformat()}: {message}")
    log_to_file(f"[BOT_EVENT] {message}")

# --- Katana Command Execution ---
def run_katana_command(command: str) -> str:
    """
    Executes a shell command and returns its output.
    This is a simplified placeholder. In a real scenario, this would interact
    with a more complex 'katana_agent' or similar.
    """
    log_local_bot_event(f"Running katana command: {command}")
    try:
        # Using shell=True for simplicity with complex commands like pipes.
        # Be cautious with shell=True in production due to security risks.
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True, timeout=30)
        output = result.stdout.strip()
        if result.stderr.strip():
            output += f"\nStderr:\n{result.stderr.strip()}"
        log_local_bot_event(f"Command output: {output}")
        return output
    except subprocess.CalledProcessError as e:
        # Check if stderr is empty or provides a generic "not found" type error
        stderr_output = e.stderr.strip()
        if "not found" in stderr_output.lower() or "no such file" in stderr_output.lower():
            error_message = f"⚠️ Команда '{command}' не найдена или не может быть исполнена."
        elif stderr_output:
            error_message = f"🚫 Ошибка при выполнении команды '{command}':\n`{stderr_output}`"
        else:
            error_message = f"🚫 Ошибка при выполнении команды '{command}' (код возврата: {e.returncode})."
        log_local_bot_event(error_message)
        return error_message
    except subprocess.TimeoutExpired:
        error_message = f"⏳ Команда '{command}' выполнялась слишком долго и была остановлена."
        log_local_bot_event(error_message)
        return error_message
    except Exception as e:
        error_message = f"💥 Произошла непредвиденная ошибка при выполнении команды '{command}': {str(e)}"
        log_local_bot_event(error_message)
        return error_message

# --- New Synapse-based Text Handler ---
@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text_message(message):
    """
    Handles incoming text messages by routing them through the new NLP engine.
    """
    chat_id = message.chat.id
    user_id = str(message.from_user.id) # Use a persistent user ID for dialogue state
    text = message.text

    log_local_bot_event(f"Received text from {user_id} in chat {chat_id}: {text}")

    # Process the message through the Synapse NLP engine
    nlp_action = process_message(user_id, text)
    log_local_bot_event(f"NLP Engine returned action: {nlp_action}")

    # Act based on the engine's response
    action_type = nlp_action.get('action')

    if action_type == 'reply':
        # The engine wants to send a message back to the user
        # (e.g., a clarification question or a final answer)
        bot.send_message(chat_id, nlp_action['text'])

    elif action_type == 'execute':
        # The engine has identified a command to run.
        # This part is a placeholder for now, as the current nlp/main.py
        # doesn't return 'execute' actions directly yet. It would be the
        # final step after slot filling is complete.
        tool = nlp_action['tool']
        params = nlp_action['params']
        # This is a simulation of how it would work:
        command_str = f"{tool} --project_name {params.get('project_name')} --date_range {params.get('date_range')}"
        output = run_katana_command(command_str)
        bot.send_message(chat_id, f"🧠 Выполняю команду:\n`{command_str}`\n\n{output}", parse_mode="Markdown")

    elif action_type == 'do_nothing':
        # The engine decided no action was necessary
        pass

    else:
        # Fallback for unknown actions
        log_local_bot_event(f"Unknown action type from NLP engine: {action_type}")
        bot.send_message(chat_id, "🤖 Произошла внутренняя ошибка в NLP-системе.")

if __name__ == '__main__':
    log_local_bot_event("Bot starting...")
    bot.polling()
    log_local_bot_event("Bot stopped.")
