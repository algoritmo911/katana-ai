import json
from datetime import datetime

COMMAND_LOG_FILE = "command_log.jsonl"

def log_command(command_id, command, args, status, result=None, error=None):
    """Logs the status of a command to the command log file."""
    log_entry = {
        "command_id": command_id,
        "command": command,
        "args": args,
        "timestamp": datetime.utcnow().isoformat(),
        "status": status,
        "result": result,
        "error": error,
    }
    with open(COMMAND_LOG_FILE, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
