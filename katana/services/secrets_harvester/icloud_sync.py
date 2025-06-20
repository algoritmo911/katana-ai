
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

from katana.logging_config import get_logger, setup_logging
import logging

logger = get_logger(__name__)

# log_message_icloud function removed, using logger directly.

# --- Core Functions ---
def get_icloud_service(username: str, password: str):
    """Connects to iCloud, handling 2FA if required."""
    logger.info(f"Attempting iCloud login for user: {username}...")
    try:
        api = PyiCloudService(username, password)
    except PyiCloudFailedLoginException as e:
        logger.error(f"iCloud login failed: {e}. Check credentials.")
        return None
    except Exception as e_conn:
        logger.error(f"iCloud connection error during PyiCloudService init: {e_conn}")
        return None

    if api.requires_2fa:
        logger.info("🔐 iCloud 2-Factor Authentication is required.")
        try:
            code = input("   Enter the 2FA code received on your Apple device: ")
            if not api.validate_2fa_code(code):
                logger.error("❌ Invalid 2FA code entered. Login failed.")
                return None
            logger.info("✅ 2FA validation successful.")
            if not api.is_trusted_session:
                 logger.warning("Session is not trusted by iCloud. You might be prompted for 2FA again soon.")
        except PyiCloud2SARequiredException:
            logger.error("2FA is required but was not handled properly or code was invalid.")
            return None
        except Exception as e_2fa:
            logger.error(f"An error occurred during 2FA validation: {e_2fa}")
            return None

    logger.info("Successfully connected to iCloud.")
    return api

def parse_secrets_from_icloud_notes(notes_service):
    """Parses KEY=VALUE secrets from all iCloud notes."""
    # Intended regex for parsing KEY=VALUE pairs, allowing spaces in value,
    # and stopping at # or end of line.
    secret_pattern = re.compile(r"^\s*([a-zA-Z0-9_.-]+)\s*=\s*([^#\n]*?)\s*(?:#.*)?$", re.MULTILINE)
    secrets = {}
    if not notes_service:
        logger.warning("Notes service object is None. Cannot parse notes.")
        return secrets

    try:
        all_notes_generator = notes_service.all()
        all_notes_list = list(all_notes_generator)
        logger.info(f"Fetched {len(all_notes_list)} notes from iCloud.")
    except Exception as e_fetch:
        logger.error(f"Could not fetch notes from iCloud: {e_fetch}")
        return secrets

    for i, note_obj in enumerate(all_notes_list):
        try:
            text_content = str(note_obj)
            note_identifier = note_obj.id if hasattr(note_obj, 'id') else f"Note_{i}"
        except Exception as e_get_text:
            logger.warning(f"Could not get text content for a note: {e_get_text}")
            continue

        if not text_content:
            logger.debug(f"Note '{note_identifier}' has no text content to parse.")
            continue

        logger.debug(f"Parsing note: '{note_identifier}'")
        matches = secret_pattern.findall(text_content)
        if matches:
            for key, value in matches:
                key = key.strip()
                value = value.strip()
                if key:
                    secrets[key] = value
                    logger.info(f"Found iCloud secret: '{key}' in note '{note_identifier}'")
        else:
            logger.debug(f"No KEY=VALUE patterns found in note '{note_identifier}'.")

    return secrets

def save_secrets_to_json_merged(new_secrets: dict, output_filename: str = DEFAULT_SECRETS_FILENAME):
    """
    Saves secrets to a JSON file, merging with existing secrets in that file.
    New secrets overwrite existing ones if keys collide.
    Backs up the original file before modification.
    """
    output_file = Path(output_filename).resolve()
    existing_secrets = {}

    if output_file.exists():
        backup_timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
        backup_filename = output_file.parent / f"{output_file.stem}_{backup_timestamp}{output_file.suffix}.bak"
        try:
            with open(output_file, 'r', encoding='utf-8') as f_orig:
                existing_secrets = json.load(f_orig)
            if not isinstance(existing_secrets, dict):
                logger.warning(f"Existing content of {output_file.name} is not a dictionary. It will be overwritten.")
                existing_secrets = {}

            output_file.rename(backup_filename)
            logger.info(f"Backed up existing secrets file {output_file.name} to {backup_filename.name}")
        except FileNotFoundError:
             logger.info(f"No existing {output_file.name} found to backup. Will create new.")
             existing_secrets = {}
        except json.JSONDecodeError as e_json:
            logger.warning(f"Could not parse existing {output_file.name} for merging: {e_json}. It will be overwritten.")
            existing_secrets = {}
            try: output_file.rename(backup_filename)
            except Exception as e_rename_corrupt: logger.error(f"Could not rename corrupted file {output_file.name}: {e_rename_corrupt}")
        except Exception as e_backup:
            logger.error(f"Could not back up or read existing secrets file {output_file.name}: {e_backup}. Proceeding with new secrets only.")
            existing_secrets = {}

    merged_secrets = existing_secrets.copy()
    merged_secrets.update(new_secrets)

    logger.info(f"Saving {len(merged_secrets)} total secrets (merged) to {output_file}...")
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(merged_secrets, f, indent=2, ensure_ascii=False)
        logger.info(f"Secrets successfully saved to {output_file}")
    except Exception as e_save:
        logger.error(f"Could not save merged secrets to {output_file}: {e_save}")

def harvest_icloud_notes_secrets(output_target_filename: str = DEFAULT_SECRETS_FILENAME):
    """Main function to orchestrate iCloud notes secret harvesting."""
    logger.info("Starting iCloud Secrets Harvester...")
    icloud_username = os.environ.get("ICLOUD_USERNAME")
    icloud_password = os.environ.get("ICLOUD_PASSWORD")

    if not icloud_username or not icloud_password:
        logger.error("Missing ICLOUD_USERNAME or ICLOUD_PASSWORD environment variables. Cannot proceed.")
        return

    icloud_api_service = get_icloud_service(icloud_username, icloud_password)

    if icloud_api_service and hasattr(icloud_api_service, 'notes') and icloud_api_service.notes:
        icloud_secrets = parse_secrets_from_icloud_notes(icloud_api_service.notes)
        if icloud_secrets:
            logger.info(f"Found {len(icloud_secrets)} secrets from iCloud notes.")
            save_secrets_to_json_merged(icloud_secrets, filename=output_target_filename)
        else:
            logger.info("No secrets found in iCloud notes matching the pattern.")
    else:
        logger.error("Could not connect to iCloud or access notes service. No secrets harvested from iCloud.")

    logger.info("iCloud Secrets Harvester finished.")

if __name__ == "__main__":
    setup_logging(log_level=logging.INFO) # Or logging.DEBUG for more verbose output
    harvest_icloud_notes_secrets(output_target_filename=DEFAULT_SECRETS_FILENAME)
