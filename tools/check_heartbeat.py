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
    if not file_path.exists():
        print(f"CRITICAL: Heartbeat file not found: {file_path}", file=sys.stderr)
        return False

    try:
        with open(file_path, "r") as f:
            timestamp_str = f.read().strip()

        if not timestamp_str:
            print(f"CRITICAL: Heartbeat file is empty: {file_path}", file=sys.stderr)
            return False

        last_heartbeat_time = float(timestamp_str)
        current_time = time.time()
        age_seconds = current_time - last_heartbeat_time

        if age_seconds > threshold_seconds:
            print(f"CRITICAL: Heartbeat is stale! Last update was {age_seconds:.0f} seconds ago (threshold: {threshold_seconds}s). File: {file_path}", file=sys.stderr)
            return False
        else:
            print(f"OK: Heartbeat is fresh. Last update was {age_seconds:.0f} seconds ago. File: {file_path}")
            return True

    except ValueError:
        print(f"CRITICAL: Heartbeat file content is not a valid timestamp: {file_path} (Content: '{timestamp_str}')", file=sys.stderr)
        return False
    except IOError as e:
        print(f"CRITICAL: Error reading heartbeat file {file_path}: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"CRITICAL: Unexpected error checking heartbeat file {file_path}: {e}", file=sys.stderr)
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
