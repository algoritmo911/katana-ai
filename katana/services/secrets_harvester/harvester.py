import gkeepapi
import json
import os
import shutil # For backing up secrets file
from datetime import datetime # For backup file timestamp
from pathlib import Path # For Path object usage within harvester
import re

# --- Configuration & Constants ---
DEFAULT_SECRETS_FILENAME = "secrets_temp.json"
DEFAULT_API_LABEL = "api" # Case-sensitive as per gkeepapi docs for findLabel

# --- Logging Helper (Simple) ---
def log_message(level, message):
    """Basic logging to stdout."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [{level.upper()}] {message}")

# --- Core Functions ---
def login_keep(username, password):
    """Logs into Google Keep. Returns Keep object on success, None on failure."""
    log_message("info", f"Attempting Google Keep login for user: {username}...")
    keep = gkeepapi.Keep()
    try:
        success = keep.login(username, password)
        if success:
            log_message("info", "Google Keep login successful.")
            return keep
        else:
            log_message("error", "Google Keep login failed. Please check credentials or use App Password for 2FA.")
            return None
    except gkeepapi.exception.LoginException as e:
        log_message("error", f"Google Keep LoginException: {e}. Ensure username/password are correct and consider App Password for 2FA.")
        return None
    except Exception as e:
        log_message("error", f"An unexpected error occurred during Google Keep login: {e}")
        return None

def find_api_notes(keep: gkeepapi.Keep, api_label_name: str = DEFAULT_API_LABEL):
    """Finds notes with the specified API label."""
    if not keep:
        log_message("warning", "Keep object is None, cannot find notes.")
        return []

    log_message("info", f"Searching for notes with label: '{api_label_name}'...")
    try:
        label = keep.findLabel(api_label_name)
        if not label:
            log_message("warning", f"Label '{api_label_name}' not found in Google Keep.")
            return []

        api_notes_list = list(keep.find(labels=[label]))

        log_message("info", f"Found {len(api_notes_list)} note(s) with label '{api_label_name}'.")
        return api_notes_list
    except Exception as e:
        log_message("error", f"Error finding notes with label '{api_label_name}': {e}")
        return []

# --- Secret Value Validation Logic ---
VALID_SECRET_PATTERNS = [
    'sk-',                # OpenAI
    'pat',                # Airtable PATs often start with 'pat'
    'pcsk_',              # Pinecone serverless
    'AIza',               # Google AI/API keys
    'ghp_', 'gho_', 'ghu_', 'ghs_', 'ghr_', # GitHub tokens
    'glpat-',             # GitLab tokens
    'xoxb-', 'xoxp-',     # Slack tokens
]
# Precompile regex for Telegram tokens for efficiency if used often.
TELEGRAM_TOKEN_REGEX = re.compile(r"^[0-9]+:[a-zA-Z0-9_-]{30,}$") # Basic regex

def is_valid_secret_value(value_string: str, key_name: str = "") -> bool:
    """
    Checks if the value_string likely represents a secret based on known patterns.
    Optionally considers the key_name for context.
    """
    if not isinstance(value_string, str) or not value_string: # Also check for empty string value
        return False

    for prefix in VALID_SECRET_PATTERNS:
        if value_string.startswith(prefix):
            return True

    if TELEGRAM_TOKEN_REGEX.match(value_string):
        return True

    return False

# --- Key Parsing Function (with validation) ---
def parse_keys_from_note_text(note_text: str):
    """
    Parses key-value pairs from the text of a single note.
    Filters keys based on is_valid_secret_value.
    """
    parsed_keys = {}
    if not note_text:
        return parsed_keys

    for line in note_text.split('\n'): # Explicitly split on newline char
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            parts = line.split('=', 1)
            key = parts[0].strip()
            value = parts[1].strip()

            if is_valid_secret_value(value, key_name=key):
                parsed_keys[key] = value
                log_message("debug", f"Accepted key '{key}' based on valid value pattern.")
            else:
                log_message("debug", f"Skipped key '{key}': value '{value[:20]}...' did not match known secret patterns.")
    return parsed_keys

def save_secrets_to_json(secrets_data: dict, filename: str = DEFAULT_SECRETS_FILENAME):
    """Saves the collected secrets data to a JSON file, backing up the old one."""
    output_file = Path(filename)

    if output_file.exists():
        backup_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = output_file.parent / f"{output_file.stem}_{backup_timestamp}{output_file.suffix}.bak"
        try:
            shutil.copyfile(output_file, backup_filename)
            log_message("info", f"Backed up existing secrets file to {backup_filename}")
        except Exception as e:
            log_message("error", f"Could not back up existing secrets file {output_file}: {e}")

    log_message("info", f"Saving secrets to {output_file}...")
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(secrets_data, f, indent=2, ensure_ascii=False)
        log_message("info", f"Secrets successfully saved to {output_file}")
    except Exception as e:
        log_message("error", f"Could not save secrets to {output_file}: {e}")

# --- Main Execution ---
if __name__ == '__main__':
    log_message("info", "Katana Secrets Harvester - Stage 1: Google Keep Parsing")

    gkeep_username = os.getenv('GKEEP_USERNAME')
    gkeep_password = os.getenv('GKEEP_PASSWORD')

    if not gkeep_username or not gkeep_password:
        log_message("error", "GKEEP_USERNAME and/or GKEEP_PASSWORD environment variables not set.")
        log_message("error", "Please set them before running the script. For 2FA accounts, use an App Password for GKEEP_PASSWORD.")
    else:
        keep_instance = login_keep(gkeep_username, gkeep_password)

        if keep_instance:
            log_message("info", "Syncing with Google Keep to fetch latest data...")
            try:
                keep_instance.sync()
                log_message("info", "Sync complete.")
            except Exception as e:
                log_message("error", f"Error during keep.sync(): {e}")

            api_notes = find_api_notes(keep_instance)

            all_extracted_keys = {}
            if api_notes:
                for note_node in api_notes:
                    log_message("debug", f"Processing note: '{note_node.title}' (ID: {note_node.id})")
                    if note_node.text:
                        keys_from_this_note = parse_keys_from_note_text(note_node.text)
                        if keys_from_this_note:
                            log_message("info", f"Found {len(keys_from_this_note)} key(s) in note '{note_node.title}': {list(keys_from_this_note.keys())}")
                            all_extracted_keys.update(keys_from_this_note)
                        else:
                            log_message("info", f"No parsable keys found in note '{note_node.title}'.")
                    else:
                        log_message("info", f"Note '{note_node.title}' has no text content to parse.")

            if all_extracted_keys:
                save_secrets_to_json(all_extracted_keys)
            else:
                log_message("warning", "No API keys found in any notes with the 'api' label, or notes had no text.")
                save_secrets_to_json({})
        else:
            log_message("error", "Could not login to Google Keep. Harvester did not run.")

    log_message("info", "Katana Secrets Harvester finished.")
