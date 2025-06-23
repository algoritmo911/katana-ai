
# katana_secrets_harvester/icloud_sync.py
from pyicloud import PyiCloudService # pip install pyicloud
from pyicloud.exceptions import PyiCloudFailedLoginException, PyiCloud2SARequiredException # More specific exceptions
import json
import re
import os
from datetime import datetime, timezone # Ensure timezone for UTC consistency
from pathlib import Path # For path operations within the script

# --- Configuration & Constants ---
DEFAULT_SECRETS_FILENAME = "secrets_temp.json"
import uuid # Added for unique message_ids

from katana.logger import get_logger, setup_logging
import logging # For logger levels if needed

logger = get_logger(__name__)

# log_message_icloud function removed, using logger directly.

# --- Core Functions ---
def get_icloud_service(username: str, password: str):
    """Connects to iCloud, handling 2FA if required."""
    op_id = str(uuid.uuid4())
    log_context = {'user_id': username or 'unknown_icloud_user', 'chat_id': 'icloud_auth', 'message_id': op_id}

    logger.info(f"Attempting iCloud login for user: {username}...", extra=log_context)
    try:
        api = PyiCloudService(username, password)
    except PyiCloudFailedLoginException as e:
        logger.error(f"iCloud login failed: {e}. Check credentials.", extra=log_context)
        return None
    except Exception as e_conn:
        logger.error(f"iCloud connection error during PyiCloudService init: {e_conn}", exc_info=True, extra=log_context)
        return None

    if api.requires_2fa:
        logger.info("🔐 iCloud 2-Factor Authentication is required.", extra=log_context)
        try:
            # Note: input() will block execution. This is typical for CLI tools needing 2FA.
            code = input("   Enter the 2FA code received on your Apple device: ")
            if not api.validate_2fa_code(code):
                logger.error("❌ Invalid 2FA code entered. Login failed.", extra=log_context)
                return None
            logger.info("✅ 2FA validation successful.", extra=log_context)
            if not api.is_trusted_session:
                 logger.warning("Session is not trusted by iCloud. You might be prompted for 2FA again soon.", extra=log_context)
        except PyiCloud2SARequiredException: # This exception might be raised by validate_2fa_code or other 2FA interactions
            logger.error("2FA is required but was not handled properly or code was invalid (PyiCloud2SARequiredException).", exc_info=True, extra=log_context)
            return None
        except Exception as e_2fa:
            logger.error(f"An error occurred during 2FA validation: {e_2fa}", exc_info=True, extra=log_context)
            return None

    logger.info("Successfully connected to iCloud.", extra=log_context)
    return api

def parse_secrets_from_icloud_notes(notes_service):
    """Parses KEY=VALUE secrets from all iCloud notes."""
    # Intended regex for parsing KEY=VALUE pairs, allowing spaces in value,
    # and stopping at # or end of line.
    secret_pattern = re.compile(r"^\s*([a-zA-Z0-9_.-]+)\s*=\s*([^#\n]*?)\s*(?:#.*)?$", re.MULTILINE)
    secrets = {}

    # Try to get username from notes_service if possible, or use a default for context
    # This assumes notes_service might be linked to an API object that has user info.
    # For pyicloud, the PyiCloudService object itself doesn't directly expose username after auth.
    # So, we'll use a generic 'icloud_user_unknown' or rely on it being passed if available.
    # For this function, a generic system context is fine for overall ops,
    # and note-specific logs will use note_identifier for message_id.
    base_user_id = 'icloud_user_unknown' # Placeholder
    base_chat_id = 'icloud_note_parsing'

    if not notes_service:
        logger.warning(
            "Notes service object is None. Cannot parse notes.",
            extra={'user_id': base_user_id, 'chat_id': base_chat_id, 'message_id': 'notes_service_none'}
        )
        return secrets

    try:
        all_notes_generator = notes_service.all()
        all_notes_list = list(all_notes_generator) # This can be slow for many notes
        logger.info(
            f"Fetched {len(all_notes_list)} notes from iCloud.",
            extra={'user_id': base_user_id, 'chat_id': base_chat_id, 'message_id': 'fetch_notes_summary', 'note_count': len(all_notes_list)}
        )
    except Exception as e_fetch:
        logger.error(
            f"Could not fetch notes from iCloud: {e_fetch}", exc_info=True,
            extra={'user_id': base_user_id, 'chat_id': base_chat_id, 'message_id': 'fetch_notes_error'}
        )
        return secrets

    for i, note_obj in enumerate(all_notes_list):
        note_identifier = note_obj.id if hasattr(note_obj, 'id') else f"NoteAtIndex_{i}"
        note_context = {'user_id': base_user_id, 'chat_id': base_chat_id, 'message_id': f'process_note_{note_identifier}'}

        try:
            text_content = str(note_obj) # This might be where content is fetched
        except Exception as e_get_text:
            logger.warning(f"Could not get text content for note '{note_identifier}': {e_get_text}", exc_info=True, extra=note_context)
            continue

        if not text_content:
            logger.debug(f"Note '{note_identifier}' has no text content to parse.", extra=note_context)
            continue

        logger.debug(f"Parsing note: '{note_identifier}'", extra=note_context)
        matches = secret_pattern.findall(text_content)
        if matches:
            for key, value in matches:
                key = key.strip()
                value = value.strip() # Value might be empty, that's fine
                if key: # Key must not be empty
                    secrets[key] = value
                    # Log found secret with specific key context
                    found_secret_context = {**note_context, 'message_id': f'found_secret_in_{note_identifier}', 'secret_key': key}
                    logger.info(f"Found iCloud secret: '{key}' in note '{note_identifier}'", extra=found_secret_context)
        else:
            logger.debug(f"No KEY=VALUE patterns found in note '{note_identifier}'.", extra=note_context)

    return secrets

def save_secrets_to_json_merged(new_secrets: dict, output_filename: str = DEFAULT_SECRETS_FILENAME):
    """
    Saves secrets to a JSON file, merging with existing secrets in that file.
    New secrets overwrite existing ones if keys collide.
    Backs up the original file before modification.
    """
    op_id = str(uuid.uuid4())
    # user_id for file operations is typically system/script itself.
    log_context_base = {'user_id': 'icloud_sync_system', 'chat_id': 'file_ops', 'message_id': op_id}

    output_file = Path(output_filename).resolve()
    existing_secrets = {}

    if output_file.exists():
        backup_timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
        backup_filename = output_file.parent / f"{output_file.stem}_{backup_timestamp}{output_file.suffix}.bak"
        try:
            with open(output_file, 'r', encoding='utf-8') as f_orig:
                existing_secrets = json.load(f_orig)
            if not isinstance(existing_secrets, dict):
                logger.warning(
                    f"Existing content of {output_file.name} is not a dictionary. It will be overwritten.",
                    extra={**log_context_base, 'message_id': f'{op_id}_existing_not_dict'}
                )
                existing_secrets = {}

            output_file.rename(backup_filename) # Move original to backup path
            logger.info(
                f"Backed up existing secrets file {output_file.name} to {backup_filename.name}",
                extra={**log_context_base, 'message_id': f'{op_id}_backup_success', "backup_file": str(backup_filename)}
            )
        except FileNotFoundError:
             logger.info(
                 f"No existing {output_file.name} found to backup. Will create new.",
                 extra={**log_context_base, 'message_id': f'{op_id}_backup_not_found'}
            )
             existing_secrets = {}
        except json.JSONDecodeError as e_json:
            logger.warning(
                f"Could not parse existing {output_file.name} for merging: {e_json}. It will be overwritten.",
                extra={**log_context_base, 'message_id': f'{op_id}_backup_parse_error'}
            )
            existing_secrets = {}
            try:
                output_file.rename(backup_filename) # Try to backup corrupted file too
            except Exception as e_rename_corrupt:
                logger.error(
                    f"Could not rename corrupted file {output_file.name} to backup: {e_rename_corrupt}",
                    exc_info=True, extra={**log_context_base, 'message_id': f'{op_id}_backup_rename_corrupt_fail'}
                )
        except Exception as e_backup:
            logger.error(
                f"Could not back up or read existing secrets file {output_file.name}: {e_backup}. Proceeding with new secrets only.",
                exc_info=True, extra={**log_context_base, 'message_id': f'{op_id}_backup_general_fail'}
            )
            existing_secrets = {}

    merged_secrets = existing_secrets.copy()
    merged_secrets.update(new_secrets)

    logger.info(f"Saving {len(merged_secrets)} total secrets (merged) to {output_file}...", extra=log_context_base)
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(merged_secrets, f, indent=2, ensure_ascii=False)
        logger.info(f"Secrets successfully saved to {output_file}", extra=log_context_base)
    except Exception as e_save:
        logger.error(f"Could not save merged secrets to {output_file}: {e_save}", exc_info=True, extra=log_context_base)

def harvest_icloud_notes_secrets(output_target_filename: str = DEFAULT_SECRETS_FILENAME):
    """Main function to orchestrate iCloud notes secret harvesting."""
    main_op_id = f"icloud_harvest_run_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    # Use a generic system ID for the overall harvester task, can be augmented with username if login succeeds.
    base_context = {'user_id': 'icloud_harvester_system', 'chat_id': 'main_sync_process', 'message_id': main_op_id}

    logger.info("Starting iCloud Secrets Harvester...", extra=base_context)

    icloud_username = os.environ.get("ICLOUD_USERNAME")
    icloud_password = os.environ.get("ICLOUD_PASSWORD")

    if not icloud_username or not icloud_password:
        logger.error(
            "Missing ICLOUD_USERNAME or ICLOUD_PASSWORD environment variables. Cannot proceed.",
            extra={**base_context, 'message_id': f'{main_op_id}_env_vars_missing'}
        )
        return

    # Update user_id in context if username is available for subsequent logs from this function
    # Note: get_icloud_service and parse_secrets_from_icloud_notes will create their own more specific contexts.
    user_specific_context = {**base_context, 'user_id': icloud_username}

    icloud_api_service = get_icloud_service(icloud_username, icloud_password)

    if icloud_api_service and hasattr(icloud_api_service, 'notes') and icloud_api_service.notes:
        # parse_secrets_from_icloud_notes has its own logging.
        # We can log a summary here based on its output.
        icloud_secrets = parse_secrets_from_icloud_notes(icloud_api_service.notes)
        if icloud_secrets:
            logger.info(
                f"Found {len(icloud_secrets)} secrets from iCloud notes for user {icloud_username}.",
                extra={**user_specific_context, 'message_id': f'{main_op_id}_secrets_found', 'secret_count': len(icloud_secrets)}
            )
            # save_secrets_to_json_merged has its own logging.
            save_secrets_to_json_merged(icloud_secrets, output_filename=output_target_filename)
        else:
            logger.info(
                f"No secrets found in iCloud notes matching the pattern for user {icloud_username}.",
                extra={**user_specific_context, 'message_id': f'{main_op_id}_no_secrets_found'}
            )
    else:
        logger.error(
            f"Could not connect to iCloud or access notes service for user {icloud_username}. No secrets harvested from iCloud.",
            extra=user_specific_context # Use user_specific here as we know the username attempt
        )

    logger.info("iCloud Secrets Harvester finished.", extra=base_context)

if __name__ == "__main__":
    # For direct script run, user_id can be specific to this execution context
    main_run_context = {'user_id': 'icloud_sync_script_run', 'chat_id': 'manual_execution', 'message_id': f"manual_run_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"}
    # Setup logging with a context that will be used if no other context is provided by a specific log call.
    # However, our practice is to provide context at each call site.
    # The setup_logging itself does not take 'extra'. This is just for the __main__ block's own direct logs.
    setup_logging(log_level=logging.INFO)

    # This initial log from __main__ will use the default "N/A" from ContextFilter
    # unless we pass 'extra' here too. For consistency, let's add it.
    logger.info("iCloud Harvester script invoked directly.", extra=main_run_context)
    harvest_icloud_notes_secrets(output_target_filename=DEFAULT_SECRETS_FILENAME)
