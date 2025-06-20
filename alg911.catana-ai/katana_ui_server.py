import os
import json
import time
import datetime # Ensure datetime is imported
from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KATANA_EVENTS_LOG = os.path.join(SCRIPT_DIR, "katana_events.log")
KATANA_COMMANDS_JSON = os.path.join(SCRIPT_DIR, "katana.commands.json")
KATANA_MEMORY_JSON = os.path.join(SCRIPT_DIR, "katana_memory.json")

# --- Flask App Setup ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_very_secret_key_here!' # IMPORTANT: Change this in production
socketio = SocketIO(app, cors_allowed_origins="*") # Allow all origins for now (dev)

# --- Global State ---
last_log_size = 0
if os.path.exists(KATANA_EVENTS_LOG):
    last_log_size = os.path.getsize(KATANA_EVENTS_LOG)

# --- Helper Functions ---
def get_katana_memory():
    if not os.path.exists(KATANA_MEMORY_JSON):
        return {}
    try:
        with open(KATANA_MEMORY_JSON, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading Katana memory: {e}")
        return {}

def get_katana_commands():
    if not os.path.exists(KATANA_COMMANDS_JSON):
        return []
    try:
        with open(KATANA_COMMANDS_JSON, 'r') as f:
            content = f.read()
            if not content.strip():
                return []
            return json.loads(content)
    except Exception as e:
        print(f"Error reading Katana commands: {e}")
        return []

def get_new_log_entries():
    global last_log_size
    new_entries = []
    if os.path.exists(KATANA_EVENTS_LOG):
        current_log_size = os.path.getsize(KATANA_EVENTS_LOG)
        if current_log_size > last_log_size:
            try:
                with open(KATANA_EVENTS_LOG, 'r') as f:
                    f.seek(last_log_size)
                    new_entries = f.readlines()
                last_log_size = current_log_size
            except Exception as e:
                print(f"Error reading new log entries: {e}")
        elif current_log_size < last_log_size:
            last_log_size = 0
            if current_log_size < 1024 * 10:
                 with open(KATANA_EVENTS_LOG, 'r') as f:
                    new_entries = f.readlines()
                 last_log_size = current_log_size
    return [entry.strip() for entry in new_entries if entry.strip()]

# --- Watchdog Event Handler ---
class LogChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path == KATANA_EVENTS_LOG:
            print(f"Detected modification in {KATANA_EVENTS_LOG}")
            new_logs = get_new_log_entries()
            if new_logs:
                print(f"Emitting {len(new_logs)} new log entries.")
                socketio.emit('new_log_entries', {'logs': new_logs})

# --- SocketIO Event Handlers ---
@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('request_initial_data')
def handle_request_initial_data(data):
    print("Client requested initial data.")
    all_logs = []
    if os.path.exists(KATANA_EVENTS_LOG):
        try:
            with open(KATANA_EVENTS_LOG, 'r') as f:
                all_logs = [line.strip() for line in f.readlines() if line.strip()]
        except Exception as e:
            print(f"Error reading full log file: {e}")
    emit('initial_data', {
        'logs': all_logs[-500:],
        'memory': get_katana_memory(),
        'commands': get_katana_commands()[:100]
    })

@socketio.on('send_command_to_katana')
def handle_send_command(data):
    client_sid = request.sid
    print(f"Received command from UI (SID: {client_sid}): {data}")

    action = data.get("action")
    raw_parameters = data.get("parameters", "{}")
    parameters = {}

    if not action:
        emit('command_response', {'success': False, 'message': 'Action is required.'}, room=client_sid)
        return

    try:
        parameters = json.loads(raw_parameters)
        if not isinstance(parameters, dict):
            raise ValueError("Parameters must be a JSON object.")
    except json.JSONDecodeError:
        emit('command_response', {'success': False, 'message': 'Invalid JSON in parameters.'}, room=client_sid)
        return
    except ValueError as ve:
        emit('command_response', {'success': False, 'message': str(ve)}, room=client_sid)
        return

    command_to_add = {
        "command_id": f"ui_cmd_{int(time.time())}_{os.urandom(2).hex()}",
        "action": action,
        "parameters": parameters,
        "source": "katana_dashboard_ui",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "processed": False,
        "status_after_execution": None,
        "result": None
    }

    try:
        current_commands = get_katana_commands()
        current_commands.append(command_to_add)

        with open(KATANA_COMMANDS_JSON, 'w') as f:
            json.dump(current_commands, f, indent=2)

        print(f"Command {command_to_add['command_id']} added to {KATANA_COMMANDS_JSON}")
        emit('command_response', {
            'success': True,
            'message': f'Command {command_to_add["command_id"]} sent to Katana.',
            'command_id': command_to_add['command_id']
        }, room=client_sid)

    except Exception as e:
        error_message = f"Error writing command to {KATANA_COMMANDS_JSON}: {e}"
        print(error_message)
        emit('command_response', {'success': False, 'message': error_message}, room=client_sid)

# --- HTTP Endpoints ---
@app.route('/api/status', methods=['GET'])
def get_status():
    status = {
        "katana_memory": get_katana_memory(),
        "pending_commands_count": len([c for c in get_katana_commands() if not c.get('processed', False)]),
        "log_file_size": os.path.getsize(KATANA_EVENTS_LOG) if os.path.exists(KATANA_EVENTS_LOG) else 0
    }
    return jsonify(status)

@app.route('/api/logs', methods=['GET'])
def get_logs():
    lines_limit = request.args.get('limit', default=200, type=int)
    all_logs = []
    if os.path.exists(KATANA_EVENTS_LOG):
        try:
            with open(KATANA_EVENTS_LOG, 'r') as f:
                all_logs = [line.strip() for line in f.readlines() if line.strip()]
        except Exception as e:
            print(f"Error reading full log file for API: {e}")
            return jsonify({"error": str(e)}), 500
    return jsonify({'logs': all_logs[-lines_limit:]})

# --- Main Execution ---
if __name__ == '__main__':
    event_handler = LogChangeHandler()
    observer = Observer()
    log_dir = os.path.dirname(KATANA_EVENTS_LOG)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
        print(f"Created log directory: {log_dir}")
    if not os.path.exists(KATANA_EVENTS_LOG):
        with open(KATANA_EVENTS_LOG, 'a'): os.utime(KATANA_EVENTS_LOG, None)
        print(f"Touched log file: {KATANA_EVENTS_LOG}")
        last_log_size = 0

    observer.schedule(event_handler, path=log_dir, recursive=False)
    observer.start()
    print(f"Watching for changes in {KATANA_EVENTS_LOG} (via its directory {log_dir})")

    print("Starting Katana UI Interaction Server...")
    socketio.run(app, host='0.0.0.0', port=5050, debug=True, use_reloader=False)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    print("Katana UI Interaction Server stopped.")
