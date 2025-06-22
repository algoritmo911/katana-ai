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
import uuid # Added for unique message_ids

from katana.logging_config import get_logger, setup_logging
import logging # For logger levels if needed

logger = get_logger(__name__)

# log_message function removed, using logger directly.

# --- Core Functions ---
def login_keep(username, password):
    """Logs into Google Keep. Returns Keep object on success, None on failure."""
    op_id = str(uuid.uuid4())
    # Use the provided username in the context if available
    log_context = {'user_id': username or 'unknown_gkeep_user', 'chat_id': 'gkeep_auth', 'message_id': op_id}

    logger.info(f"Attempting Google Keep login for user: {username}...", extra=log_context)
    keep = gkeepapi.Keep()
    try:
        success = keep.login(username, password)
        if success:
            logger.info("Google Keep login successful.", extra=log_context)
            return keep
        else:
            logger.error("Google Keep login failed. Please check credentials or use App Password for 2FA.", extra=log_context)
            return None
    except gkeepapi.exception.LoginException as e:
        logger.error(f"Google Keep LoginException: {e}. Ensure username/password are correct and consider App Password for 2FA.", extra=log_context)
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during Google Keep login: {e}", exc_info=True, extra=log_context)
        return None

def find_api_notes(keep: gkeepapi.Keep, api_label_name: str = DEFAULT_API_LABEL):
    """Finds notes with the specified API label."""
    op_id = str(uuid.uuid4())
    # Try to get username from keep object if possible, otherwise use a default
    username = keep.username if hasattr(keep, 'username') and keep.username else 'gkeep_user_unknown'
    log_context = {'user_id': username, 'chat_id': 'gkeep_ops', 'message_id': op_id}

    if not keep:
        logger.warning("Keep object is None, cannot find notes.", extra=log_context)
        return []

    logger.info(f"Searching for notes with label: '{api_label_name}'...", extra=log_context)
    try:
        label = keep.findLabel(api_label_name)
        if not label:
            logger.warning(f"Label '{api_label_name}' not found in Google Keep.", extra=log_context)
            return []

        api_notes_list = list(keep.find(labels=[label]))

        logger.info(f"Found {len(api_notes_list)} note(s) with label '{api_label_name}'.", extra=log_context)
        return api_notes_list
    except Exception as e:
        logger.error(f"Error finding notes with label '{api_label_name}': {e}", exc_info=True, extra=log_context)
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
    # Context for parsing a specific note's text. message_id could be note_id if available,
    # but it's not passed here. So, a generic one for the operation.
    # Assuming user_id context would be handled by the caller of this utility function.
    # For internal debugs, a simple context or inheriting from caller is fine.
    # Let's use a generic one for these low-level debugs.
    parse_debug_context = {'user_id': 'secrets_parser', 'chat_id': 'note_parsing_detail', 'message_id': 'parse_note_text_internal'}

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
                logger.debug(f"Accepted key '{key}' based on valid value pattern.", extra={**parse_debug_context, "parsed_key": key})
            else:
                logger.debug(f"Skipped key '{key}': value '{value[:20]}...' did not match known secret patterns.", extra={**parse_debug_context, "skipped_key": key})
    return parsed_keys

def save_secrets_to_json(secrets_data: dict, filename: str = DEFAULT_SECRETS_FILENAME):
    """Saves the collected secrets data to a JSON file, backing up the old one."""
    op_id = str(uuid.uuid4())
    # User for saving secrets is typically system/script itself.
    save_context = {'user_id': 'secrets_harvester_system', 'chat_id': 'file_ops', 'message_id': op_id}

    output_file = Path(filename)

    if output_file.exists():
        backup_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = output_file.parent / f"{output_file.stem}_{backup_timestamp}{output_file.suffix}.bak"
        try:
            shutil.copyfile(output_file, backup_filename)
            logger.info(f"Backed up existing secrets file to {backup_filename}", extra={**save_context, "backup_file": str(backup_filename)})
        except Exception as e:
            logger.error(f"Could not back up existing secrets file {output_file}: {e}", exc_info=True, extra=save_context)

    logger.info(f"Saving secrets to {output_file}...", extra=save_context)
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(secrets_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Secrets successfully saved to {output_file}", extra=save_context)
    except Exception as e:
        logger.error(f"Could not save secrets to {output_file}: {e}", exc_info=True, extra=save_context)

# --- Main Execution ---
if __name__ == '__main__':
    setup_logging(log_level=logging.DEBUG) # DEBUG to see key acceptance/skipping.

    main_op_id = f"harvester_main_run_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    # For __main__, user_id can represent the script/system itself.
    main_context = {'user_id': 'secrets_harvester_script', 'chat_id': 'main_execution', 'message_id': main_op_id}

    logger.info("Katana Secrets Harvester - Stage 1: Google Keep Parsing", extra=main_context)

    gkeep_username = os.getenv('GKEEP_USERNAME')
    gkeep_password = os.getenv('GKEEP_PASSWORD')

    if not gkeep_username or not gkeep_password:
        env_fail_context = {**main_context, 'message_id': f"{main_op_id}_env_var_missing"}
        logger.error("GKEEP_USERNAME and/or GKEEP_PASSWORD environment variables not set.", extra=env_fail_context)
        logger.error("Please set them before running the script. For 2FA accounts, use an App Password for GKEEP_PASSWORD.", extra=env_fail_context)
    else:
        # login_keep and find_api_notes use their own internal logging with context
        keep_instance = login_keep(gkeep_username, gkeep_password)

        if keep_instance:
            sync_context = {'user_id': gkeep_username, 'chat_id': 'gkeep_sync', 'message_id': f"{main_op_id}_sync"}
            logger.info("Syncing with Google Keep to fetch latest data...", extra=sync_context)
            try:
                keep_instance.sync()
                logger.info("Sync complete.", extra=sync_context)
            except Exception as e:
                logger.error(f"Error during keep.sync(): {e}", exc_info=True, extra=sync_context)

            api_notes = find_api_notes(keep_instance) # Uses its own context

            all_extracted_keys = {}
            if api_notes:
                for note_idx, note_node in enumerate(api_notes):
                    note_process_context = {
                        'user_id': gkeep_username,
                        'chat_id': 'gkeep_note_process',
                        'message_id': f"{main_op_id}_process_note_{note_node.id or note_idx}"
                    }
                    logger.debug(f"Processing note: '{note_node.title}' (ID: {note_node.id})", extra=note_process_context)
                    if note_node.text:
                        # parse_keys_from_note_text has its own low-level debug logs
                        keys_from_this_note = parse_keys_from_note_text(note_node.text)
                        if keys_from_this_note:
                            logger.info(
                                f"Found {len(keys_from_this_note)} key(s) in note '{note_node.title}': {list(keys_from_this_note.keys())}",
                                extra=note_process_context
                            )
                            all_extracted_keys.update(keys_from_this_note)
                        else:
                            logger.info(f"No parsable keys found in note '{note_node.title}'.", extra=note_process_context)
                    else:
                        logger.info(f"Note '{note_node.title}' has no text content to parse.", extra=note_process_context)

            # save_secrets_to_json has its own logging with context
            if all_extracted_keys:
                save_secrets_to_json(all_extracted_keys)
            else:
                no_keys_ctx = {**main_context, 'user_id': gkeep_username, 'message_id': f"{main_op_id}_no_keys_found"}
                logger.warning("No API keys found in any notes with the 'api' label, or notes had no text.", extra=no_keys_ctx)
                save_secrets_to_json({}) # Save empty dict to indicate it ran and found nothing
        else:
            login_fail_ctx = {**main_context, 'user_id': gkeep_username, 'message_id': f"{main_op_id}_login_fail"}
            logger.error("Could not login to Google Keep. Harvester did not run.", extra=login_fail_ctx)

    logger.info("Katana Secrets Harvester finished.", extra={**main_context, 'message_id': f"{main_op_id}_finished"})
