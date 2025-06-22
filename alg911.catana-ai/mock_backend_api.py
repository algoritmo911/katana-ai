import logging
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
import os
import time
import threading # Required for background task with 'threading' async_mode
from collections import deque # For efficiently getting last N lines
import re # For parsing log lines

# Attempt to import from cli_integration
try:
    from cli_integration import send_command_to_cli, KATANA_AGENT_SCRIPT_PATH, setup_backend_logger
    # Use the centralized logger setup from cli_integration.py
    logger = setup_backend_logger(__name__, logging.INFO)
except ImportError:
    # Fallback basic logging if cli_integration is not found (e.g. during initial setup or if standalone)
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s')
    logger = logging.getLogger(__name__)
    logger.warning("Could not import setup_backend_logger from cli_integration. Using basicConfig for logging.")
    # Define KATANA_AGENT_SCRIPT_PATH if it's not imported, for _KATANA_AGENT_DIR usage below
    if 'KATANA_AGENT_SCRIPT_PATH' not in globals():
        KATANA_AGENT_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "katana_agent.py") # Best guess
    def send_command_to_cli(action, parameters): # Placeholder if import failed
        logger.warning("Using placeholder send_command_to_cli due to import error from cli_integration.")
        return {"status": "error", "message": "cli_integration.send_command_to_cli not available."}

# Ensure KATANA_AGENT_SCRIPT_PATH is defined for _KATANA_AGENT_DIR usage, even if cli_integration failed to import fully
if 'KATANA_AGENT_SCRIPT_PATH' not in globals():
    logger.error("KATANA_AGENT_SCRIPT_PATH is not defined. This should not happen if cli_integration was imported.")
    KATANA_AGENT_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "katana_agent.py") # Fallback path

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'your_default_secret_key_here!')
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")

_KATANA_AGENT_DIR = os.path.dirname(KATANA_AGENT_SCRIPT_PATH)
KATANA_EVENTS_LOG_PATH = os.path.join(_KATANA_AGENT_DIR, "katana_events.log")

LOG_TAIL_LINES = 100
LOG_POLL_INTERVAL = 1

# Log level management
LOG_LEVEL_VALUES = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50, "UNKNOWN": 0}
DEFAULT_CLIENT_LOG_LEVEL = "INFO"
client_log_levels = {}  # Stores SID -> log_level_string

# Regex to parse log lines from katana_events.log (FileHandler format)
# Example: [2024-01-25T12:35:07,123+0000] [INFO] [katana_logger] [katana_agent._execute_echo_command:295] Echoing arguments: ['hello']
LOG_LINE_REGEX = re.compile(
    r"\[(.*?)\]\s+"       # Timestamp (group 1)
    r"\[(DEBUG|INFO|WARNING|ERROR|CRITICAL)\]\s+"  # Level (group 2)
    r"\[(.*?)\]\s+"       # Logger Name (group 3)
    r"\[(.*?)\.(.*?):(\d+)\]\s+" # Module.funcName:lineno (groups 4, 5, 6)
    r"(.*)"               # Message (group 7)
)

def parse_log_line(line_str: str) -> dict | None:
    """Parses a log line string into a dictionary."""
    match = LOG_LINE_REGEX.match(line_str)
    if match:
        return {
            "timestamp": match.group(1),
            "level": match.group(2),
            "logger_name": match.group(3),
            "module": match.group(4),
            "function": match.group(5),
            "lineno": match.group(6),
            "message": match.group(7).strip(),
            "raw": line_str.strip() # Keep raw line as well
        }
    # Try a simpler parsing for console logs or other formats as a fallback
    parts = line_str.strip().split('] [')
    if len(parts) >= 3: # Basic check for common pattern like [time] [LEVEL] [source] msg
        try:
            timestamp = parts[0].lstrip('[')
            level = parts[1].split(']')[0]
            # Heuristic to see if level is valid, otherwise UNKNOWN
            if level.upper() not in LOG_LEVEL_VALUES:
                level = "UNKNOWN" # or try to extract from message

            # The rest is message, potentially with source part too
            message_part = '] ['.join(parts[2:])
            return {
                "timestamp": timestamp, "level": level.upper(), "message": message_part.strip(),
                "logger_name": "unknown", "module": "unknown", "function": "unknown", "lineno": "0",
                "raw": line_str.strip()
            }
        except Exception: # If any error during this basic parsing
            pass

    logger.debug(f"Could not parse log line: {line_str[:100]}") # Log only snippet
    return {"timestamp": "unknown", "level": "UNKNOWN", "message": line_str.strip(), "raw": line_str.strip()}


def get_filtered_log_lines(filepath, n, requested_level_str):
    """Reads and filters the last n lines from a file based on log level."""
    raw_lines = []
    if not os.path.exists(filepath):
        logger.warning(f"Log file not found for filtering: {filepath}")
        return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            raw_lines = list(deque(f, n))
    except Exception as e:
        logger.error(f"Error reading log file {filepath} for filtering: {e}")
        return []

    filtered_lines = []
    requested_level_val = LOG_LEVEL_VALUES.get(requested_level_str.upper(), LOG_LEVEL_VALUES[DEFAULT_CLIENT_LOG_LEVEL])

    for line_str in raw_lines:
        parsed_line = parse_log_line(line_str)
        if parsed_line:
            line_level_val = LOG_LEVEL_VALUES.get(parsed_line["level"], LOG_LEVEL_VALUES["UNKNOWN"])
            if line_level_val >= requested_level_val:
                filtered_lines.append(parsed_line["raw"]) # Send raw line
    return filtered_lines

def tail_log_file_thread():
    logger.info(f"Starting log tailing thread for {KATANA_EVENTS_LOG_PATH}...")

    while True:
        try:
            with open(KATANA_EVENTS_LOG_PATH, 'r', encoding='utf-8') as f:
                logger.info(f"Log file {KATANA_EVENTS_LOG_PATH} opened for tailing.")
                f.seek(0, 2)

                while True:
                    line_str = f.readline()
                    if not line_str:
                        time.sleep(LOG_POLL_INTERVAL)
                        continue

                    parsed_line = parse_log_line(line_str)
                    if not parsed_line:
                        # Optionally decide if unparseable lines go to any client (e.g. DEBUG clients)
                        # For now, we only proceed if we can determine a level
                        continue

                    line_level_val = LOG_LEVEL_VALUES.get(parsed_line["level"], LOG_LEVEL_VALUES["UNKNOWN"])

                    # Iterate over a copy of keys if modifications can happen
                    active_sids = list(client_log_levels.keys())
                    for sid in active_sids:
                        if sid not in socketio.server.eio.sockets: # Check if socket still connected
                            client_log_levels.pop(sid, None) # Clean up if disconnected
                            continue

                        client_pref_level_str = client_log_levels.get(sid, DEFAULT_CLIENT_LOG_LEVEL)
                        client_pref_level_val = LOG_LEVEL_VALUES.get(client_pref_level_str.upper(), LOG_LEVEL_VALUES[DEFAULT_CLIENT_LOG_LEVEL])

                        if line_level_val >= client_pref_level_val:
                            socketio.emit('new_log_lines', {'logs': [parsed_line["raw"]]}, room=sid)
        except FileNotFoundError:
            logger.warning(f"Log file {KATANA_EVENTS_LOG_PATH} not found. Retrying in {LOG_POLL_INTERVAL * 5}s...")
            time.sleep(LOG_POLL_INTERVAL * 5)
        except Exception as e:
            logger.error(f"Error in log tailing thread: {e}. Restarting tailing attempt...")
            time.sleep(LOG_POLL_INTERVAL * 2)

@socketio.on('connect')
def handle_connect():
    sid = request.sid
    logger.info(f"Client {sid} connected to SocketIO log stream.")
    client_log_levels[sid] = DEFAULT_CLIENT_LOG_LEVEL # Set default level

    initial_lines = get_filtered_log_lines(KATANA_EVENTS_LOG_PATH, LOG_TAIL_LINES, client_log_levels[sid])
    if initial_lines:
        emit('initial_logs', {'logs': initial_lines}) # Emits to the connecting client only
        logger.info(f"Sent {len(initial_lines)} initial log lines (level {client_log_levels[sid]}) to client {sid}.")
    else:
        emit('initial_logs', {'logs': [f"No logs found for level {client_log_levels[sid]} or log file not accessible."]})

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    removed_level = client_log_levels.pop(sid, None)
    logger.info(f"Client {sid} disconnected (was level: {removed_level}).")

@socketio.on('set_filter_level')
def handle_set_filter_level(data):
    sid = request.sid
    new_level = data.get('level', DEFAULT_CLIENT_LOG_LEVEL).upper()

    if new_level not in LOG_LEVEL_VALUES:
        logger.warning(f"Client {sid} requested invalid log level: {new_level}. Using default.")
        new_level = DEFAULT_CLIENT_LOG_LEVEL
        emit('filter_status', {'status': 'error', 'message': f"Invalid level '{data.get('level')}'. Defaulted to {new_level}."})


    client_log_levels[sid] = new_level
    logger.info(f"Client {sid} set log filter level to: {new_level}")
    emit('filter_status', {'status': 'success', 'level': new_level}) # Confirm level change to client

    # Re-send initial logs with new filter
    initial_lines = get_filtered_log_lines(KATANA_EVENTS_LOG_PATH, LOG_TAIL_LINES, new_level)
    if initial_lines:
        emit('initial_logs', {'logs': initial_lines})
        logger.info(f"Sent {len(initial_lines)} historical log lines (new level {new_level}) to client {sid}.")
    else:
        emit('initial_logs', {'logs': [f"No logs found for level {new_level} or log file not accessible."]})


# --- Flask HTTP Routes ---
@app.route('/api/command', methods=['POST'])
def handle_api_command():
    logger.info(f"Received request for /api/command from {request.remote_addr}")
    # ... (rest of the /api/command handler remains the same) ...
    if not request.is_json:
        logger.error("Request is not JSON")
        return jsonify({"status": "error", "message": "Invalid request: payload must be JSON."}), 400

    data = request.get_json()
    logger.info(f"Request data: {data}")

    action = data.get('action')
    parameters = data.get('parameters', {})

    if not action:
        logger.error("'action' field is missing in request.")
        return jsonify({"status": "error", "message": "'action' field is required."}), 400

    if not isinstance(action, str):
        logger.error("'action' field must be a string.")
        return jsonify({"status": "error", "message": "'action' field must be a string."}), 400

    if not isinstance(parameters, dict):
        logger.error("'parameters' field must be a dictionary.")
        return jsonify({"status": "error", "message": "'parameters' field must be a dictionary."}), 400

    logger.info(f"Calling send_command_to_cli with action: '{action}', parameters: {parameters}")

    cli_response = send_command_to_cli(action, parameters)
    logger.info(f"Response from send_command_to_cli: {cli_response}")

    response_payload = cli_response
    http_status_code = 500

    if cli_response.get("status") == "error":
        http_status_code = 500
        logger.error(f"Sending HTTP 500 response due to error in cli_integration: {response_payload.get('message')}")
    elif cli_response.get("status") == "success":
        http_status_code = 200
        log_level = logging.INFO
        if cli_response.get("task_status") == "failed":
            log_level = logging.WARNING
        logger.log(log_level, f"Sending HTTP 200 response. Task status: {cli_response.get('task_status')}, Result: {str(cli_response.get('result', 'N/A'))[:100]}")
    else:
        logger.error(f"Unexpected response structure from send_command_to_cli: {cli_response}. Sending HTTP 500.")
        response_payload = {
            "status": "error",
            "message": "Internal error: Unexpected response from CLI integration."
        }
        http_status_code = 500

    return jsonify(response_payload), http_status_code

if __name__ == '__main__':
    logger.info("Starting mock backend API server with SocketIO on http://localhost:5000")

    if 'send_command_to_cli' in globals() and hasattr(globals()['send_command_to_cli'], '__module__') and globals()['send_command_to_cli'].__module__ == 'cli_integration':
         logger.info(f"Katana agent script path used by cli_integration: {KATANA_AGENT_SCRIPT_PATH}")
         logger.info(f"Monitoring Katana events log at: {KATANA_EVENTS_LOG_PATH}")
    else:
        logger.warning(f"cli_integration.py might not be imported correctly. KATANA_AGENT_SCRIPT_PATH and KATANA_EVENTS_LOG_PATH may not be accurate.")

    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
        log_tail_thread = threading.Thread(target=tail_log_file_thread, daemon=True)
        log_tail_thread.start()
        logger.info("Log tailing background thread started.")
    elif app.debug:
        logger.info("Log tailing background thread will start with the reloader's main process.")

    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=True)
```
