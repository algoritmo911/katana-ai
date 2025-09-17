#!/bin/bash
# Script to synchronize the alg911.catana-ai directory to a cloud provider using rclone.
# Also includes simulated backup rotation logic.

# --- Configuration ---
# Base directory of the Katana AI project (where this script is located)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Path to the rclone configuration file
RCLONE_CONFIG_FILE="${SCRIPT_DIR}/rclone.conf"

# Source directory for general sync (the Katana AI project directory itself)
SOURCE_DIR="${SCRIPT_DIR}"

# Default remote destination (e.g., "gdrive_katana:KatanaProjectBackup")
# This should match a configured remote in rclone.conf
# Example: If rclone.conf has [myCloud], this could be "myCloud:KatanaBackups"
DEFAULT_REMOTE_NAME="katana_gdrive_backup" # Default rclone remote name from rclone.conf
DEFAULT_REMOTE_PATH="KatanaCloudSync"   # Default path on the remote

# Directory containing backups made by the 'backup_data' command
LOCAL_BACKUPS_DIR="${SCRIPT_DIR}/backups"

# Log file for this script's operations (appends to Katana's main event log)
LOG_FILE_PATH="${SCRIPT_DIR}/katana_events.log" # This should be an absolute path or relative to SCRIPT_DIR

# --- Logging Function ---
log_sync_message() {
    local level="$1"
    local message="$2"
    # Ensure TIMESTAMP is current for each log message for accuracy
    local TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${TIMESTAMP}] ${level^^}: [CloudSyncScript] ${message}" >> "${LOG_FILE_PATH}"
}

# --- Argument Parsing (Placeholder for future enhancement) ---
TARGET_REMOTE="${DEFAULT_REMOTE_NAME}:${DEFAULT_REMOTE_PATH}"
SYNC_TARGET="all" # Could be "all", "backups_only", "logs_only" etc.

log_sync_message "info" "Starting cloud synchronization process."
log_sync_message "info" "Using rclone config: ${RCLONE_CONFIG_FILE}"
log_sync_message "info" "Source directory: ${SOURCE_DIR}"
log_sync_message "info" "Target remote: ${TARGET_REMOTE}"
log_sync_message "info" "Sync target type: ${SYNC_TARGET}"


# --- Main Sync Logic ---
ACTUAL_RCLONE_SYNC_COMMAND="rclone sync \"${SOURCE_DIR}\" \"${TARGET_REMOTE}/current_state\" --config \"${RCLONE_CONFIG_FILE}\" --verbose --create-empty-src-dirs"
log_sync_message "info" "SIMULATED Full Sync Command: ${ACTUAL_RCLONE_SYNC_COMMAND}"
log_sync_message "info" "Full sync to ${TARGET_REMOTE}/current_state SIMULATED successfully."


# --- Backup Rotation Simulation ---
LOCAL_BACKUP_FILES_TO_SYNC_PATTERN="${LOCAL_BACKUPS_DIR}/*.tar.gz" # Pattern for ls
REMOTE_BACKUPS_PATH="${TARGET_REMOTE}/archived_backups"

log_sync_message "info" "Starting backup archive synchronization to ${REMOTE_BACKUPS_PATH}."

# Check if there are any local backup files
# Use find to handle cases with no matches gracefully, and to correctly handle spaces in names (though not expected here)
backup_files_found=$(find "${LOCAL_BACKUPS_DIR}" -maxdepth 1 -name '*.tar.gz' -print -quit)

if [ -n "$backup_files_found" ]; then
    ACTUAL_RCLONE_BACKUP_SYNC_COMMAND="rclone sync \"${LOCAL_BACKUPS_DIR}\" \"${REMOTE_BACKUPS_PATH}\" --config \"${RCLONE_CONFIG_FILE}\" --include \"*.tar.gz\" --verbose"
    log_sync_message "info" "SIMULATED Backup Sync Command: ${ACTUAL_RCLONE_BACKUP_SYNC_COMMAND}"
    log_sync_message "info" "Backup sync to ${REMOTE_BACKUPS_PATH} SIMULATED successfully."

    KEEP_N_BACKUPS=3
    log_sync_message "info" "Simulating backup rotation: Keep last ${KEEP_N_BACKUPS} backups on remote '${REMOTE_BACKUPS_PATH}'."

    # Simulate listing remote files by listing local ones, sorted by modification time (newest first)
    # In a real rclone setup, this would be:
    # rclone lsjson "${REMOTE_BACKUPS_PATH}" --config "${RCLONE_CONFIG_FILE}" | jq -r '.[] | "\(.ModTime)\t\(.Path)"' | sort -r | cut -f2
    SIMULATED_REMOTE_FILES=$(ls -1t "${LOCAL_BACKUPS_DIR}"/*.tar.gz 2>/dev/null)

    COUNT=0
    FILES_TO_DELETE_SIMULATED=""
    # Loop through files, newest first. Delete files older than the Nth.
    # Note: IFS change is to handle spaces in filenames if they were to occur.
    OLD_IFS="$IFS"
    IFS=$'\n'
    for file_basename in $(echo "${SIMULATED_REMOTE_FILES}" | sed "s|${LOCAL_BACKUPS_DIR}/||g"); do # Get just basenames
        COUNT=$((COUNT+1))
        if [ ${COUNT} -gt ${KEEP_N_BACKUPS} ]; then
            FILES_TO_DELETE_SIMULATED="${FILES_TO_DELETE_SIMULATED}${file_basename} "
            # Real command: rclone deletefile "${REMOTE_BACKUPS_PATH}/${file_basename}" --config "${RCLONE_CONFIG_FILE}" >> "${LOG_FILE_PATH}" 2>&1
        fi
    done
    IFS="$OLD_IFS"

    if [ -n "${FILES_TO_DELETE_SIMULATED}" ]; then
        log_sync_message "info" "SIMULATED Deleting older remote backups: ${FILES_TO_DELETE_SIMULATED}"
    else
        log_sync_message "info" "No old remote backups to delete (or fewer than ${KEEP_N_BACKUPS} backups exist) - simulation based on local files."
    fi
else
    log_sync_message "info" "No local backup archives (*.tar.gz) found in ${LOCAL_BACKUPS_DIR} to sync."
fi

log_sync_message "info" "Cloud synchronization process finished (simulated)."
# Removed explicit exit 0 to comply with sandbox guidelines for run_in_bash_session
