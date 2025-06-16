import json
import datetime
import os
import subprocess

# --- File Path Constants ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COMMANDS_FILE = os.path.join(SCRIPT_DIR, "katana.commands.json")
LOG_FILE = os.path.join(SCRIPT_DIR, "katana_events.log")
NEURO_REFUELING_LOG_FILE = os.path.join(SCRIPT_DIR, "neuro_refueling", "alternatives_log.json")
MIND_CLEARING_LOG_FILE = os.path.join(SCRIPT_DIR, "mind_clearing", "thought_patterns.json")

AGENT_LOG_PREFIX = "[Katana Agent SDK]"

# --- Logging Function ---
def log_message(level, message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {level.upper()}: {AGENT_LOG_PREFIX} {message}\n")

# --- Generic JSON File Handling Functions ---
def load_json_file(file_path, log_prefix="JSONLoad"):
    if not os.path.exists(file_path):
        log_message("error", f"[{log_prefix}] File not found: {file_path}")
        return None
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        log_message("info", f"[{log_prefix}] Successfully loaded data from {file_path}.")
        return data
    except json.JSONDecodeError:
        log_message("error", f"[{log_prefix}] Error decoding JSON from {file_path}.")
        return None
    except Exception as e:
        log_message("error", f"[{log_prefix}] Error reading file {file_path}: {e}")
        return None

def save_json_file(data, file_path, log_prefix="JSONSave"):
    try:
        dir_path = os.path.dirname(file_path)
        if dir_path:
             os.makedirs(dir_path, exist_ok=True)
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
        log_message("info", f"[{log_prefix}] Successfully saved updates to {file_path}.")
        return True
    except Exception as e:
        log_message("error", f"[{log_prefix}] Error saving data to {file_path}: {e}")
        return False

# --- Command-Specific File Handling ---
def load_commands():
    return load_json_file(COMMANDS_FILE, "CommandsLoad")

def save_commands(data):
    return save_json_file(data, COMMANDS_FILE, "CommandsSave")

# --- Neuro-Refueling Module Functions ---
def handle_log_ethanol_alternative(params):
    log_message("info", f"[NeuroRefueling] Attempting to log ethanol alternative: {params}")
    alternative_name = params.get("alternative_name"); effect = params.get("effect")
    event_date = params.get("date", datetime.datetime.now().isoformat())
    craving_event = params.get("craving_event", "N/A")
    if not alternative_name or not effect:
        log_message("warning", "[NeuroRefueling] Missing 'alternative_name' or 'effect'."); return {"status": "failed", "message": "Missing 'alternative_name' or 'effect'."}
    neuro_dir = os.path.dirname(NEURO_REFUELING_LOG_FILE)
    if not os.path.exists(neuro_dir): os.makedirs(neuro_dir, exist_ok=True); log_message("info", f"[NeuroRefueling] Created directory {neuro_dir}.")
    data = load_json_file(NEURO_REFUELING_LOG_FILE, "NeuroRefuelingLoad")
    if data is None:
        log_message("info", f"[NeuroRefueling] Initializing {NEURO_REFUELING_LOG_FILE}.")
        data = {"user_id": "default", "log_entries": [], "alternative_strategies": []}
    new_log_entry = {"timestamp": event_date, "craving_event": craving_event, "chosen_alternative": alternative_name, "effect": effect, "notes": params.get("notes", "")}
    if "log_entries" not in data or not isinstance(data["log_entries"], list): data["log_entries"] = []
    data["log_entries"].append(new_log_entry)
    if save_json_file(data, NEURO_REFUELING_LOG_FILE, "NeuroRefuelingSave"):
        log_message("info", f"[NeuroRefueling] Logged: {alternative_name}"); return {"status": "success", "message": "Ethanol alternative logged."}
    else:
        log_message("error", "[NeuroRefueling] Failed to save log."); return {"status": "error", "message": "Failed to save neuro-refueling data."}

# --- Mind Clearing Module Functions ---
def handle_clear_background_thought(params):
    log_message("info", f"[MindClearing] Attempting to clear background thought: {params}")
    thought_id_to_clear = params.get("thought_id")
    thought_description_to_clear = params.get("thought_description")

    if not thought_id_to_clear and not thought_description_to_clear:
        log_message("warning", "[MindClearing] Missing 'thought_id' or 'thought_description' in parameters.")
        return {"status": "failed", "message": "Missing 'thought_id' or 'thought_description'."}

    # Ensure the directory for MIND_CLEARING_LOG_FILE exists
    mind_dir = os.path.dirname(MIND_CLEARING_LOG_FILE)
    if not os.path.exists(mind_dir):
        os.makedirs(mind_dir, exist_ok=True)
        log_message("info", f"[MindClearing] Created directory {mind_dir} for thought patterns log.")

    data = load_json_file(MIND_CLEARING_LOG_FILE, "MindClearingLoad")
    if data is None : # If file truly doesn't exist or is totally unreadable
        log_message("info", f"[MindClearing] Initializing {MIND_CLEARING_LOG_FILE} due to load failure.")
        data = {"user_id": "default", "background_thoughts": [], "mind_silence_log": []}

    # Ensure background_thoughts list exists and is a list
    if "background_thoughts" not in data or not isinstance(data["background_thoughts"], list):
        log_message("warning", "[MindClearing] 'background_thoughts' missing or not a list. Initializing.")
        data["background_thoughts"] = []


    initial_thought_count = len(data["background_thoughts"])
    thoughts_after_removal = []
    cleared_at_least_one = False

    for thought in data["background_thoughts"]:
        matches_id = thought_id_to_clear and thought.get("thought_id") == thought_id_to_clear
        matches_description = thought_description_to_clear and thought.get("description") == thought_description_to_clear

        if matches_id or matches_description:
            log_message("info", f"[MindClearing] Clearing thought: ID '{thought.get('thought_id')}', Desc: '{thought.get('description')}'")
            cleared_at_least_one = True
            continue
        thoughts_after_removal.append(thought)

    data["background_thoughts"] = thoughts_after_removal

    if not cleared_at_least_one:
        log_message("info", f"[MindClearing] No thought found matching ID '{thought_id_to_clear}' or Desc '{thought_description_to_clear}'.")
        return {"status": "success", "message": "No matching thought found to clear."} # Still a success, nothing to do

    if save_json_file(data, MIND_CLEARING_LOG_FILE, "MindClearingSave"):
        cleared_count = initial_thought_count - len(data["background_thoughts"])
        log_message("info", f"[MindClearing] Successfully cleared {cleared_count} thought(s).")
        return {"status": "success", "message": f"Successfully cleared {cleared_count} thought(s)."}
    else:
        log_message("error", "[MindClearing] Failed to save updated mind-clearing log.")
        return {"status": "error", "message": "Failed to save mind-clearing data after attempting removal."}

# --- Cloud Sync Function ---
def sync_logs_to_cloud():
    log_message("info", "Attempting to synchronize logs to cloud...")
    script_path = os.path.join(SCRIPT_DIR, "sync_to_cloud.sh")
    if not os.path.exists(script_path):
        log_message("error", f"sync_to_cloud.sh not found at {script_path}"); return {"status": "error", "message": f"sync_to_cloud.sh not found at {script_path}"}
    try:
        os.chmod(script_path, 0o755)
        process = subprocess.run([script_path], capture_output=True, text=True, check=True, cwd=SCRIPT_DIR)
        log_message("info", f"sync_to_cloud.sh executed. Stout: {process.stdout.strip()}. Stderr: {process.stderr.strip()}")
        return {"status": "success", "message": "Log synchronization script executed.", "stdout": process.stdout.strip(), "stderr": process.stderr.strip()}
    except subprocess.CalledProcessError as e:
        log_message("error", f"sync_to_cloud.sh failed: {e}. Stout: {e.stdout.strip()}. Stderr: {e.stderr.strip()}"); return {"status": "error", "message": f"sync_to_cloud.sh failed: {e}", "stdout": e.stdout.strip(), "stderr": e.stderr.strip()}
    except Exception as e:
        log_message("error", f"Unexpected error in sync_logs_to_cloud: {e}"); return {"status": "error", "message": f"Unexpected error: {e}"}

# --- Main Command Processing Logic ---
def process_next_command():
    log_message("info", "Checking for commands...")
    commands_data = load_commands()
    if not commands_data or not commands_data.get("commands"): log_message("info", "No commands found."); return
    processed_a_command = False
    for command in commands_data["commands"]:
        if command.get("status") == "pending":
            log_message("info", f"Processing cmd: {command.get('command_id')}, action: {command.get('action')}")
            action = command.get("action"); params = command.get("parameters", {}); command["result"] = {}
            if action == "status_check":
                command["status"] = "completed"; command["result"].update({"status": "OK", "message": "System nominal."})
            elif action == "log_event":
                event_level=params.get("level","info"); event_type=params.get("event_type","generic"); details=params.get("details","No details.")
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(LOG_FILE, "a") as f: f.write(f"[{timestamp}] {event_level.upper()}: [USER EVENT] Type: {event_type}, Details: {details}\n")
                command["status"] = "completed"; command["result"].update({"status": "LOGGED", "message": "User event recorded."})
            elif action == "run_shell":
                shell_cmd = params.get("shell_command")
                if not shell_cmd: command["status"] = "failed"; command["result"].update({"error": "No shell_command."})
                elif not any(shell_cmd.strip().startswith(p) for p in ["ls","echo","pwd"]): command["status"] = "failed"; command["result"].update({"error": "Shell command not allowed."})
                else:
                    try:
                        proc = subprocess.run(shell_cmd, shell=True, capture_output=True, text=True, timeout=30)
                        out=proc.stdout.strip(); err=proc.stderr.strip(); command["result"].update({"stdout":out, "stderr":err})
                        if proc.returncode == 0: command["status"] = "completed"; log_message("info", f"Shell success. OUT: {out}")
                        else: command["status"] = "failed"; log_message("error", f"Shell failed. RC:{proc.returncode} ERR:{err} OUT:{out}")
                    except Exception as e: command["status"] = "failed"; command["result"].update({"error":str(e)})
            elif action == "sync_logs":
                res = sync_logs_to_cloud(); command["result"].update(res)
                command["status"] = "completed" if res.get("status") == "success" else "failed"
            elif action == "log_ethanol_alternative":
                res = handle_log_ethanol_alternative(params); command["result"].update(res)
                command["status"] = "completed" if res.get("status") == "success" else res.get("status", "failed")
            elif action == "clear_background_thought":
                res = handle_clear_background_thought(params); command["result"].update(res)
                command["status"] = "completed" if res.get("status") == "success" else res.get("status", "failed")
            else:
                command["status"] = "failed"; command["result"].update({"error": "Unknown action type"})
            command["processed_timestamp"] = datetime.datetime.now().isoformat()
            processed_a_command = True; break
    if processed_a_command:
        if not save_commands(commands_data): log_message("critical", "Failed to save commands data post-processing!")
    else: log_message("info", "No pending commands.")

if __name__ == "__main__":
    log_message("info", "Katana Agent SDK script started.")
    process_next_command()
    log_message("info", "Katana Agent SDK script finished.")
