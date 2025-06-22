#!/usr/bin/env python3
import argparse
import os
import sys
import time
from pathlib import Path

DEFAULT_HEARTBEAT_FILENAME = "katana_heartbeat.txt"
DEFAULT_THRESHOLD_SECONDS = 120  # 2 minutes

def check_heartbeat(file_path: Path, threshold_seconds: int) -> bool:
    """
    Checks the heartbeat file.

    Args:
        file_path: Path to the heartbeat file.
        threshold_seconds: Maximum allowed age of the heartbeat in seconds.

    Returns:
        True if heartbeat is okay, False otherwise.
    """
DEFAULT_ALERT_CONTACT_TELEGRAM = "@admin_user_or_group"
DEFAULT_ALERT_CONTACT_EMAIL = "admin@example.com"

def simulate_alert(reason: str, details: str):
    """
    Simulates sending an alert. In a real scenario, this would integrate
    with an actual notification service (Telegram, Email, PagerDuty, etc.).
    """
    alert_message = f"ALERT TRIGGERED: {reason}\nDetails: {details}\n" \
                    f"Simulated notification to:\n" \
                    f"  Telegram: {DEFAULT_ALERT_CONTACT_TELEGRAM}\n" \
                    f"  Email: {DEFAULT_ALERT_CONTACT_EMAIL}"
    print(alert_message, file=sys.stderr) # Print alerts to stderr for cron jobs to capture

def check_heartbeat(file_path: Path, threshold_seconds: int) -> bool:
    """
    Checks the heartbeat file.

    Args:
        file_path: Path to the heartbeat file.
        threshold_seconds: Maximum allowed age of the heartbeat in seconds.

    Returns:
        True if heartbeat is okay, False otherwise.
    """
    if not file_path.exists():
        reason = "Heartbeat file not found"
        details = f"File: {file_path}"
        print(f"CRITICAL: {reason} - {details}", file=sys.stderr)
        simulate_alert(reason, details)
        return False

    timestamp_str = "" # Define in broader scope for use in except ValueError
    try:
        with open(file_path, "r") as f:
            timestamp_str = f.read().strip()

        if not timestamp_str:
            reason = "Heartbeat file is empty"
            details = f"File: {file_path}"
            print(f"CRITICAL: {reason} - {details}", file=sys.stderr)
            simulate_alert(reason, details)
            return False

        last_heartbeat_time = float(timestamp_str)
        current_time = time.time()
        age_seconds = current_time - last_heartbeat_time

        if age_seconds > threshold_seconds:
            reason = "Heartbeat is stale"
            details = f"Last update was {age_seconds:.0f} seconds ago (threshold: {threshold_seconds}s). File: {file_path}"
            print(f"CRITICAL: {reason} - {details}", file=sys.stderr)
            simulate_alert(reason, details)
            return False
        else:
            print(f"OK: Heartbeat is fresh. Last update was {age_seconds:.0f} seconds ago. File: {file_path}")
            return True

    except ValueError:
        reason = "Heartbeat file content is not a valid timestamp"
        details = f"File: {file_path} (Content: '{timestamp_str}')"
        print(f"CRITICAL: {reason} - {details}", file=sys.stderr)
        simulate_alert(reason, details)
        return False
    except IOError as e:
        reason = "Error reading heartbeat file"
        details = f"File: {file_path}, Error: {e}"
        print(f"CRITICAL: {reason} - {details}", file=sys.stderr)
        simulate_alert(reason, details)
        return False
    except Exception as e:
        reason = "Unexpected error checking heartbeat file"
        details = f"File: {file_path}, Error: {e}"
        print(f"CRITICAL: {reason} - {details}", file=sys.stderr)
        simulate_alert(reason, details)
        return False

if __name__ == "__main__":
    # Default path assumes the script is in 'tools/' and heartbeat file is in the parent directory (project root)
    project_root = Path(__file__).resolve().parent.parent
    default_file_path_str = str(project_root / DEFAULT_HEARTBEAT_FILENAME)

    parser = argparse.ArgumentParser(description="Check Katana Bot heartbeat file.")
    parser.add_argument(
        "--file",
        type=str,
        default=default_file_path_str,
        help=f"Path to the heartbeat file (default: {default_file_path_str})"
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=DEFAULT_THRESHOLD_SECONDS,
        help=f"Maximum allowed age of the heartbeat in seconds (default: {DEFAULT_THRESHOLD_SECONDS})"
    )

    args = parser.parse_args()

    heartbeat_ok = check_heartbeat(Path(args.file), args.threshold)

    if heartbeat_ok:
        sys.exit(0)
    else:
        sys.exit(1) # Exit with non-zero status for CRITICAL issues
