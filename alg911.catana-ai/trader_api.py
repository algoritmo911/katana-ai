import os
import json
import datetime
import uuid
from flask import Flask, request, jsonify

# --- Configuration ---
import shared_config  # Now we assume shared_config.py is present

COMMANDS_FILE = shared_config.COMMANDS_FILE_PATH
log_event = shared_config.log_event  # Use the shared logger

# Initialize Flask app
app = Flask(__name__)
COMPONENT_PREFIX = "TraderAPI"  # For logging


# --- Helper Functions ---
def load_commands(file_path):
    """Loads commands from the JSON file."""
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r") as f:
            content = f.read()
            if not content.strip():  # File is empty
                return []
            data = json.loads(content)
        return data
    except json.JSONDecodeError:
        log_event(
            f"Error decoding JSON from {file_path}. Returning empty list.",
            "error",
            COMPONENT_PREFIX,
        )
        return []
    except Exception as e:
        log_event(
            f"Unexpected error loading {file_path}: {e}. Returning empty list.",
            "error",
            COMPONENT_PREFIX,
        )
        return []


def save_commands(file_path, commands_list):
    """Saves commands to the JSON file."""
    try:
        dir_name = os.path.dirname(file_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
        with open(file_path, "w") as f:
            json.dump(commands_list, f, indent=2)
        # log_event(f"Successfully saved JSON to {file_path}.", "debug", COMPONENT_PREFIX) # Can be too verbose
        return True
    except Exception as e:
        log_event(f"Error saving JSON to {file_path}: {e}", "error", COMPONENT_PREFIX)
        return False


# --- API Endpoints ---
@app.route("/trader/command", methods=["POST"])
def post_trader_command():
    """
    Receives a command for the trader, adds it to the command queue.
    Expects JSON payload, e.g.,
    {
        "command_type": "BUY_STOCK",
        "symbol": "AAPL",
        "quantity": 100,
        "price_limit": 150.00,
        "source": "trader_api"
    }
    """
    if not request.is_json:
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    data = request.get_json()
    command_type = data.get("command_type")
    source = data.get("source", "trader_api")  # Default source

    if not command_type:
        return (
            jsonify(
                {"status": "error", "message": "Missing 'command_type' in request"}
            ),
            400,
        )

    # Construct the command object
    new_command = {
        "command_id": str(uuid.uuid4()),
        "timestamp_received_api": datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),
        "command_details": data,  # Store the whole payload
        "status": "pending",  # Initial status
        "source": source,
    }

    # Load existing commands, append new one, and save
    # This needs to be concurrency-safe if multiple writers are expected,
    # but for now, a simple load-append-save will do.
    # For production, a proper queue or database would be better.
    commands_list = load_commands(COMMANDS_FILE)
    commands_list.append(new_command)

    if save_commands(COMMANDS_FILE, commands_list):
        log_event(
            f"Received command: {command_type}. ID: {new_command['command_id']}", "info"
        )
        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Command received and queued.",
                    "command_id": new_command["command_id"],
                }
            ),
            201,
        )
    else:
        log_event(f"Failed to save command: {command_type}", "error")
        return (
            jsonify({"status": "error", "message": "Failed to save command to queue"}),
            500,
        )


@app.route("/trader/status", methods=["GET"])
def get_trader_status():
    """A simple status endpoint for the trader API."""
    # This could be expanded to check connectivity to other services, etc.
    return (
        jsonify(
            {
                "status": "ok",
                "message": "Trader API is running.",
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
        ),
        200,
    )


if __name__ == "__main__":
    # Make sure COMMANDS_FILE path is correctly set before running
    if not os.path.isabs(
        COMMANDS_FILE
    ):  # If it's a relative path, make it absolute from script dir
        COMMANDS_FILE = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), COMMANDS_FILE
        )

    log_event(
        f"Trader API starting. Commands will be written to: {COMMANDS_FILE}", "info"
    )

    # Ensure the command file exists with an empty list if it's new
    if not os.path.exists(COMMANDS_FILE):
        save_commands(COMMANDS_FILE, [])
        log_event(f"Initialized empty commands file at {COMMANDS_FILE}", "info")
    elif os.path.getsize(COMMANDS_FILE) == 0:  # If file exists but is empty
        save_commands(COMMANDS_FILE, [])
        log_event(f"Initialized (was empty) commands file at {COMMANDS_FILE}", "info")

    app.run(host="0.0.0.0", port=5001, debug=True)
