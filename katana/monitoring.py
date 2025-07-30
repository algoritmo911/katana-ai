import time
import os
from dotenv import load_dotenv

load_dotenv()

KatanaStats = {
    "uptime": 0,
    "commands_received": 0,
    "last_command_ts": None,
    "dry_run": os.environ.get("DRY_RUN", "false").lower() == "true",
    "build_version": os.environ.get("KATANA_BUILD_VERSION", "unknown"),
    "last_command_echo": None,
}

start_time = time.time()

def get_uptime():
    """Calculates the uptime and returns it in a human-readable format."""
    uptime_seconds = time.time() - start_time
    days, rem = divmod(uptime_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    uptime_str = ""
    if days > 0:
        uptime_str += f"{int(days)}d "
    if hours > 0:
        uptime_str += f"{int(hours)}h "
    if minutes > 0:
        uptime_str += f"{int(minutes)}m "
    uptime_str += f"{int(seconds)}s"
    return uptime_str.strip()

def increment_command_count(command: str = None):
    """Increments the processed command counter and updates the last command info."""
    KatanaStats["commands_received"] += 1
    KatanaStats["last_command_ts"] = time.time()
    if command:
        KatanaStats["last_command_echo"] = command

def get_stats():
    """Returns the current statistics."""
    KatanaStats["uptime"] = get_uptime()
    return KatanaStats
