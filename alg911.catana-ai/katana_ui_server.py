import os
from flask import Flask, jsonify, request
from flask_socketio import SocketIO
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from backend.socket_handlers import (
    get_katana_memory,
    get_katana_commands,
    handle_send_command,
    handle_ping_agent,
    handle_reload_settings_command,
    KATANA_EVENTS_LOG,
    KATANA_MEMORY_JSON,
    KATANA_COMMANDS_JSON,
    tracked_commands, # Import the new shared dictionary
    get_katana_commands as load_all_commands_from_file # Alias to avoid confusion with the other get_katana_commands
)
import json # For loading commands file

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_very_secret_key_here!'
socketio = SocketIO(app, cors_allowed_origins="*")

last_log_size = 0
if os.path.exists(KATANA_EVENTS_LOG):
    last_log_size = os.path.getsize(KATANA_EVENTS_LOG)

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

class LogChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path == KATANA_EVENTS_LOG:
            print(f"katana_ui_server: Detected modification in {KATANA_EVENTS_LOG}")
            new_logs = get_new_log_entries()
            if new_logs:
                print(f"katana_ui_server: Emitting {len(new_logs)} new log entries.")
                socketio.emit('new_log_entries', {'logs': new_logs})

class CommandStatusHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path == KATANA_COMMANDS_JSON:
            print(f"katana_ui_server: Detected modification in {KATANA_COMMANDS_JSON}")
            try:
                # It's possible the file is being written as we read it, so handle potential errors
                current_commands_on_disk = load_all_commands_from_file()
                if not current_commands_on_disk: # File might be temporarily empty or unreadable
                    print(f"katana_ui_server: {KATANA_COMMANDS_JSON} is currently empty or unreadable. Skipping processing.")
                    return

                processed_ids_in_this_check = []
                for command_id_tracked, client_sid in list(tracked_commands.items()): # Iterate on a copy for safe removal
                    # Find the command in the list from the file
                    command_in_file = next((cmd for cmd in current_commands_on_disk if cmd.get("command_id") == command_id_tracked), None)

                    if command_in_file and command_in_file.get("processed"):
                        print(f"katana_ui_server: Command {command_id_tracked} has been processed. Notifying client {client_sid}.")
                        socketio.emit('command_completed', {
                            'command_id': command_id_tracked,
                            'status': command_in_file.get('status_after_execution'),
                            'result': command_in_file.get('result'),
                            'processed_at': command_in_file.get('processed_at_utc')
                        }, room=client_sid)
                        processed_ids_in_this_check.append(command_id_tracked)

                for pid in processed_ids_in_this_check:
                    if pid in tracked_commands:
                        del tracked_commands[pid] # Clean up tracked command
                        print(f"katana_ui_server: Removed {pid} from tracked_commands.")

            except json.JSONDecodeError:
                print(f"katana_ui_server: Error decoding {KATANA_COMMANDS_JSON} during status check. File might be mid-write. Will retry.")
            except Exception as e:
                print(f"katana_ui_server: Error processing command status update from {KATANA_COMMANDS_JSON}: {e}")


@socketio.on('connect')
def handle_connect():
    print('katana_ui_server: Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('katana_ui_server: Client disconnected')

socketio.on_event('send_command_to_katana', handle_send_command)
socketio.on_event('ping_agent', handle_ping_agent) # <--- Ensure correct name
socketio.on_event('reload_settings_command', handle_reload_settings_command) # <--- Ensure correct name

@socketio.on('request_initial_data')
def handle_request_initial_data(data):
    print("katana_ui_server: Client requested initial data.")
    all_logs = []
    if os.path.exists(KATANA_EVENTS_LOG):
        try:
            with open(KATANA_EVENTS_LOG, 'r') as f:
                all_logs = [line.strip() for line in f.readlines() if line.strip()]
        except Exception as e:
            print(f"Error reading full log file: {e}")
            all_logs = [f"Error reading logs: {str(e)}"]

    socketio.emit('initial_data', {
        'logs': all_logs[-500:],
        'memory': get_katana_memory(),
        'commands': get_katana_commands()[:100]
    })

@app.route('/api/status', methods=['GET'])
def get_status_api():
    status_data = {
        "katana_memory": get_katana_memory(),
        "pending_commands_count": len([c for c in get_katana_commands() if not c.get('processed', False)]),
    }
    if os.path.exists(KATANA_EVENTS_LOG):
        status_data["log_file_size"] = os.path.getsize(KATANA_EVENTS_LOG)
    else:
        status_data["log_file_size"] = 0
    return jsonify(status_data)

@app.route('/api/logs', methods=['GET'])
def get_logs_api():
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

if __name__ == '__main__':
    event_handler = LogChangeHandler()
    observer = Observer()
    log_dir = os.path.dirname(KATANA_EVENTS_LOG)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    if not os.path.exists(KATANA_EVENTS_LOG): # Ensure log file exists
        with open(KATANA_EVENTS_LOG, 'a'): os.utime(KATANA_EVENTS_LOG, None)
        last_log_size = 0
    observer.schedule(event_handler, path=log_dir, recursive=False) # For logs

    # Setup for command status monitoring
    commands_event_handler = CommandStatusHandler()
    commands_file_path = KATANA_COMMANDS_JSON
    commands_dir = os.path.dirname(commands_file_path)
    if not os.path.exists(commands_dir): # Should exist based on agent init, but good practice
        os.makedirs(commands_dir, exist_ok=True)
    if not os.path.exists(commands_file_path): # Ensure commands file exists
        with open(commands_file_path, 'w') as f:
            json.dump([], f)
        print(f"katana_ui_server: Initialized empty {KATANA_COMMANDS_JSON} as it was missing.")

    # It's better to watch the directory containing the file if the file might be replaced (e.g. atomic write by some editors/systems)
    # However, given our agent appends/modifies, watching the file directly via its directory is fine.
    observer.schedule(commands_event_handler, path=commands_dir, recursive=False) # For commands

    observer.start()
    print(f"katana_ui_server: Watching for log changes in {log_dir}")
    print(f"katana_ui_server: Watching for command status changes in {commands_dir} (for {os.path.basename(KATANA_COMMANDS_JSON)})")
    print("katana_ui_server: Starting Katana UI Interaction Server...")
    socketio.run(app, host='0.0.0.0', port=5050, debug=True, use_reloader=False)
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    print("katana_ui_server: Katana UI Interaction Server stopped.")
