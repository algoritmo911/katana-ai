import os
import json
import time
import datetime
import psutil # For system metrics
from flask import request
from flask_socketio import emit

HANDLER_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KATANA_BASE_DIR = os.path.dirname(HANDLER_SCRIPT_DIR)

KATANA_EVENTS_LOG = os.path.join(KATANA_BASE_DIR, "katana_events.log")
KATANA_COMMANDS_JSON = os.path.join(KATANA_BASE_DIR, "katana.commands.json")
KATANA_MEMORY_JSON = os.path.join(KATANA_BASE_DIR, "katana_memory.json")

SERVER_START_TIME = time.time()
AGENT_VERSION = "0.1.1-ui-backend" # Updated version placeholder

# Helper function to get current process memory/cpu
def get_process_metrics():
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    return {
        "rss_mb": mem_info.rss / (1024 * 1024),  # Resident Set Size in MB
        "vms_mb": mem_info.vms / (1024 * 1024),  # Virtual Memory Size in MB
        "cpu_percent": process.cpu_percent(interval=0.1) # Non-blocking, short interval
    }

def get_katana_memory():
    if not os.path.exists(KATANA_MEMORY_JSON):
        return {}
    try:
        with open(KATANA_MEMORY_JSON, 'r') as f:
            content = f.read().strip()
            if not content: return {}
            return json.loads(content)
    except Exception as e:
        print(f"Error reading Katana memory: {e}")
        return {}

def get_katana_commands():
    if not os.path.exists(KATANA_COMMANDS_JSON):
        return []
    try:
        with open(KATANA_COMMANDS_JSON, 'r') as f:
            content = f.read().strip()
            if not content: return []
            return json.loads(content)
    except json.JSONDecodeError:
        print(f"Warning: {KATANA_COMMANDS_JSON} is not valid JSON or is empty. Returning empty list.")
        return []
    except Exception as e:
        print(f"Error reading Katana commands: {e}")
        return []

def handle_send_command(data):
    client_sid = request.sid
    print(f"socket_handlers: Received command from UI (SID: {client_sid}): {data}")
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
        print(f"socket_handlers: Command {command_to_add['command_id']} added to {KATANA_COMMANDS_JSON}")
        emit('command_response', {
            'success': True,
            'message': f'Command {command_to_add["command_id"]} sent to Katana.',
            'command_id': command_to_add['command_id']
        }, room=client_sid)
    except Exception as e:
        error_message = f"Error writing command to {KATANA_COMMANDS_JSON}: {e}"
        print(f"socket_handlers: {error_message}")
        emit('command_response', {'success': False, 'message': error_message}, room=client_sid)

def handle_ping_agent(data): # Renamed from placeholder
    client_sid = request.sid
    print(f"socket_handlers: Received ping_agent from UI (SID: {client_sid}): {data}")
    uptime_seconds = time.time() - SERVER_START_TIME
    process_metrics = get_process_metrics()

    metrics = {
        "server_uptime_seconds": int(uptime_seconds),
        "server_time_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "agent_version": AGENT_VERSION,
        "process_metrics": process_metrics,
        "message": "Pong from Katana UI backend server!"
    }
    # Also, add this ping to katana.commands.json so the agent itself knows about it
    # This is optional for a ping that just checks UI backend, but good for consistency
    ping_command_for_agent = {
        "command_id": f"ui_ping_{int(time.time())}",
        "action": "ping_received_from_ui_backend", # Agent can log this
        "parameters": {"source_sid": client_sid, "server_metrics_at_ping": metrics},
        "source": "katana_ui_server_ping_handler",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "processed": False # Agent will process this log
    }
    try:
        current_commands = get_katana_commands()
        current_commands.append(ping_command_for_agent)
        with open(KATANA_COMMANDS_JSON, 'w') as f:
            json.dump(current_commands, f, indent=2)
    except Exception as e:
        print(f"socket_handlers: Error logging ping to commands file: {e}")

    emit('agent_response', {'status': 'success', 'type': 'ping_response', 'data': metrics}, room=client_sid)

def handle_reload_settings_command(data): # Renamed from placeholder
    client_sid = request.sid
    print(f"socket_handlers: Received reload_settings_command from UI (SID: {client_sid}): {data}")

    command_action_for_agent = "reload_core_settings" # The actual action for katana_agent.py
    command_to_add = {
        "command_id": f"ui_cmd_reload_{int(time.time())}_{os.urandom(2).hex()}",
        "action": command_action_for_agent,
        "parameters": data.get("parameters", {}), # Pass any params from UI if needed
        "source": "katana_dashboard_ui_reload_handler",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "processed": False
    }
    try:
        current_commands = get_katana_commands()
        current_commands.append(command_to_add)
        with open(KATANA_COMMANDS_JSON, 'w') as f:
            json.dump(current_commands, f, indent=2)

        print(f"socket_handlers: Command {command_to_add['command_id']} ({command_action_for_agent}) added to {KATANA_COMMANDS_JSON}")
        emit('agent_response', {
            'status': 'success',
            'type': 'reload_response',
            'message': f'Command {command_action_for_agent} sent to Katana agent. Check logs for agent processing status.',
            'command_id': command_to_add['command_id']
        }, room=client_sid)
    except Exception as e:
        error_message = f"Error sending {command_action_for_agent} command to agent: {e}"
        print(f"socket_handlers: {error_message}")
        emit('agent_response', {
            'status': 'error',
            'type': 'reload_response',
            'message': error_message
        }, room=client_sid)
