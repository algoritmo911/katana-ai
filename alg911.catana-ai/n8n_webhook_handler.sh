#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
COMMANDS_FILE="${SCRIPT_DIR}/katana.commands.json"
LOG_FILE="${SCRIPT_DIR}/katana_events.log"
TMP_PAYLOAD_FILE="${SCRIPT_DIR}/.tmp_n8n_payload.json" # For passing payload to Python

log_handler_message() {
    local level="$1"; local message="$2"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${level^^}: [N8N_HANDLER] ${message}" >> "${LOG_FILE}"
}

if [ -z "$1" ]; then
    log_handler_message "error" "No JSON payload provided."
    echo "Error: No JSON payload provided."
    exit 1
fi
JSON_PAYLOAD="$1"
log_handler_message "info" "Received payload: ${JSON_PAYLOAD}"

# Write payload to a temporary file for Python to read
echo "${JSON_PAYLOAD}" > "${TMP_PAYLOAD_FILE}"
if [ $? -ne 0 ]; then
    log_handler_message "error" "Failed to write payload to temporary file."
    # exit 1 # Deferred exit to after Python block
fi

COMMAND_ID="cmd_n8n_$(date +%s)_$(uuidgen | cut -d'-' -f1)"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Check if TMP_PAYLOAD_FILE was created successfully before attempting Python part
if [ ! -f "${TMP_PAYLOAD_FILE}" ]; then
    log_handler_message "error" "Temporary payload file not created. Aborting Python execution."
    exit 1 # Exit if temp file wasn't created
fi

python3 << EOF_PYTHON_ADD_CMD
import json
import os
import sys

commands_f = "${COMMANDS_FILE}"
tmp_payload_f = "${TMP_PAYLOAD_FILE}"
cmd_id = "${COMMAND_ID}"
ts = "${TIMESTAMP}"

def log_py(level, msg):
    print(f"[PYTHON_IN_HANDLER] {level.upper()}: {msg}", file=sys.stderr)

try:
    with open(tmp_payload_f, 'r') as pf:
        parameters_obj = json.load(pf)

    new_command = {
        "command_id": cmd_id,
        "timestamp": ts,
        "action": "process_telegram_command",
        "parameters": parameters_obj,
        "status": "pending",
        "origin": "n8n_webhook"
    }

    current_data = {}
    if os.path.exists(commands_f):
        try:
            with open(commands_f, 'r') as f:
                current_data = json.load(f)
        except json.JSONDecodeError:
            log_py("error", f"Commands file {commands_f} corrupted. Initializing.")
            current_data = {"schema_version": "1.0.0", "commands": [], "pending_tasks": []}
    else:
        log_py("info", f"Commands file {commands_f} not found. Initializing.")
        current_data = {"schema_version": "1.0.0", "commands": [], "pending_tasks": []}

    if 'commands' not in current_data or not isinstance(current_data['commands'], list):
        current_data['commands'] = []

    current_data['commands'].append(new_command)

    with open(commands_f, 'w') as f:
        json.dump(current_data, f, indent=2)

    log_py("info", f"Python script successfully added command {cmd_id} to {commands_f}")
    print(f"Command {cmd_id} successfully added to Katana queue by Python script.") # Output for n8n

except json.JSONDecodeError as e:
    log_py("error", f"Invalid JSON in temp payload file {tmp_payload_f}: {e}")
    sys.exit(1) # Python script exits, not the main shell script immediately
except Exception as e:
    log_py("error", f"Python script failed: {e}")
    sys.exit(1) # Python script exits
finally:
    if os.path.exists(tmp_payload_f):
        os.remove(tmp_payload_f)
EOF_PYTHON_ADD_CMD

PY_EXIT_STATUS=$?
if [ ${PY_EXIT_STATUS} -ne 0 ]; then
    log_handler_message "error" "Python script failed to add command (Exit code: ${PY_EXIT_STATUS}). Payload: ${JSON_PAYLOAD}"
    echo "Error: Python script failed to process and queue command."
    exit 1 # Main shell script exits
fi

log_handler_message "info" "Command ${COMMAND_ID} successfully processed and added by handler."
exit 0 # Main shell script exits successfully
