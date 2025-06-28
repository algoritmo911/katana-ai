import argparse
import argparse
import os
import sys
import threading
import time # Will be needed for daemonization logic / status checks
import json # For reading status file
import datetime # For formatting timestamps

# Ensure the project root is in sys.path to allow imports from self_healing, etc.
# This assumes cli.py is in alg911.catana-ai/
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Conditional import for SelfHealingOrchestrator
try:
    from self_healing.orchestrator import SelfHealingOrchestrator
    from self_healing import self_healing_config # To check if module is enabled
    SELF_HEALING_AVAILABLE = True
except ImportError as e:
    SELF_HEALING_AVAILABLE = False
    # We'll print a message if the user tries to use self-heal commands
    # rather than failing at startup of the CLI itself.
    # print(f"Warning: Self-healing module not available or import error: {e}", file=sys.stderr)

# --- PID File Management ---
PID_DIR = PROJECT_ROOT # Store PID file in the main alg911.catana-ai directory for now
SELF_HEAL_PID_FILE = os.path.join(PID_DIR, "self_healing_daemon.pid")

def is_daemon_running():
    """Checks if the daemon is running based on the PID file."""
    if not os.path.exists(SELF_HEAL_PID_FILE):
        return False
    try:
        with open(SELF_HEAL_PID_FILE, "r") as f:
            pid = int(f.read().strip())
        # Check if process exists (OS-dependent)
        # Simple check for POSIX:
        if os.name == 'posix':
            try:
                os.kill(pid, 0) # Send signal 0, doesn't kill but checks existence
            except OSError:
                return False # No such process or permission error (assume not running for simplicity)
            else:
                return pid # Return PID if running
        # Basic check for Windows (less reliable without psutil):
        # This just checks if a process with that PID could exist, not if it's *our* process.
        # A more robust check would involve `psutil` or `tasklist` and filtering by name.
        elif os.name == 'nt':
            # This is a very naive check for Windows. `os.kill` with signal 0 doesn't work.
            # A common approach is to try to open the process, but it's complex without psutil.
            # For now, on Windows, if PID file exists, we'll be less certain.
            # Consider psutil.pid_exists(pid)
            print("Warning: Robust PID check on Windows requires 'psutil'. Assuming daemon might be running if PID file exists.", file=sys.stderr)
            return pid # Tentatively return PID
        return False # Default for other OS or if check fails
    except (IOError, ValueError):
        # PID file corrupted or unreadable
        return False

def start_self_healing_daemon():
    """Starts the SelfHealingOrchestrator in a background thread."""
    if not SELF_HEALING_AVAILABLE:
        print("Error: Self-healing module is not available. Cannot start daemon.", file=sys.stderr)
        sys.exit(1)

    if not self_healing_config.MODULE_ENABLED:
        print("Info: Self-healing module is disabled in its configuration (self_healing_config.py). Daemon will not start.", file=sys.stdout)
        # We might still write a PID file with a special value or no PID file,
        # so 'status' can report it's configured off. For now, just exit.
        sys.exit(0)

    # Check PID file existence first
    pid_file_exists = os.path.exists(SELF_HEAL_PID_FILE)
    if pid_file_exists:
        running_pid = is_daemon_running() # is_daemon_running checks process health
        if running_pid:
            print(f"Self-Healing Daemon appears to be already running with PID: {running_pid}. (Checked via {SELF_HEAL_PID_FILE})")
            print("If this is incorrect, ensure the process is stopped and remove the PID file if necessary.")
            return
        else:
            print(f"Stale PID file found ({SELF_HEAL_PID_FILE}). Removing it before starting.")
            try:
                os.remove(SELF_HEAL_PID_FILE)
            except OSError as e:
                print(f"Warning: Could not remove stale PID file {SELF_HEAL_PID_FILE}: {e}", file=sys.stderr)
                # Depending on policy, might want to exit or continue carefully

    # Proceed to start if not already effectively running
    print("Starting Katana Self-Healing Daemon in the background...")

    # The orchestrator's start() method is a blocking loop. Run in a thread.
    # For true daemonization (detaching from terminal, etc.), more complex setup is needed
    # (e.g., double fork, or using a library like python-daemon).
    # This simple threading approach means it runs as long as the parent (this CLI script)
    # is alive, OR if the thread is a daemon thread and the main thread exits.
    # For a CLI command that exits, the thread needs to be robust.

    # A more robust daemonization would involve `os.fork()` (POSIX) or `multiprocessing.Process`
    # which can be detached.
    # For now, we'll use a thread and write a PID. This is not a true OS daemon.

    try:
        orchestrator = SelfHealingOrchestrator() # Initialize it; it checks its own config.MODULE_ENABLED
        if not orchestrator.is_enabled: # Double check if orchestrator disabled itself
             print("Info: Self-Healing Orchestrator initialized but is internally disabled. Not starting healing loop.", file=sys.stdout)
             sys.exit(0)

        # We need a way for the thread to write its *actual* PID if it were a separate process.
        # If it's a thread, the PID is that of the current Python process.
        # This is a limitation of running as a thread from a short-lived CLI command.
        # A better daemon would manage its own PID file *after* forking.

        # Simplified approach for now: the PID written is the CLI's PID when it starts the thread.
        # This isn't ideal for long-term daemon management.
        pid = os.getpid()

        # Start the orchestrator in a daemon thread.
        # Python's main thread will exit once this CLI command finishes,
        # and daemon threads are terminated when all non-daemon threads exit.
        # This means the self-healing thread will NOT persist if started this way from a CLI
        # that then exits.
        #
        # To make it persist, it needs to be a true daemon process.
        # This is a significant step up in complexity (os.fork, python-daemon library).
        #
        # For this iteration, let's assume the 'run' command is intended to start it
        # within a context where the main Katana process itself might be long-lived,
        # or we accept this limitation for now.
        # The prompt "SelfHealDaemon" implies a persistent process.

        # --- THIS WILL NOT WORK FOR A TRUE DAEMON ---
        # healing_thread = threading.Thread(target=orchestrator.start, name="SelfHealingThread", daemon=True)
        # healing_thread.start()
        # print(f"Self-Healing thread started within PID {pid}. Note: This thread will exit if the main process that launched it exits.")
        # --- END NOT WORKING FOR TRUE DAEMON ---

        # TODO: Implement proper daemonization (e.g., using python-daemon or os.fork)
        # For now, this command will just print what it *would* do and exit.
        # This is a placeholder until daemonization strategy is chosen.
        print("Placeholder: Proper daemonization required.")
        print(f"If daemonized, PID would be written to: {SELF_HEAL_PID_FILE}")
        print(f"Orchestrator would be started: orchestrator.start()")

        # Simulate PID file creation.
        # This block is reached if no actively running daemon was detected.
        try:
            # In a real daemon, the daemon process itself writes this *after* forking.
            with open(SELF_HEAL_PID_FILE, "w") as f:
                f.write(str(os.getpid())) # Placeholder: current process PID
            print(f"Placeholder PID file created: {SELF_HEAL_PID_FILE} with PID {os.getpid()}")
            print("Warning: This is a placeholder. The self-healing process is NOT truly daemonized yet.")
        except IOError as e:
            print(f"Error: Could not write PID file {SELF_HEAL_PID_FILE}: {e}", file=sys.stderr)
            sys.exit(1)

        # In a real daemon, the parent process (CLI) would exit here.
        # The child (daemon) process would continue.

    except Exception as e:
        print(f"Error starting Self-Healing Orchestrator: {e}", file=sys.stderr)
        sys.exit(1)


def handle_self_heal_run(args):
    start_self_healing_daemon()

def handle_self_heal_status(args):
    if not SELF_HEALING_AVAILABLE:
        print("Error: Self-healing module is not available. Cannot get status.", file=sys.stderr)
        sys.exit(1)

    print("Katana Self-Healing Status:")

    status_file_path = os.path.join(PROJECT_ROOT, "self_healing_status.json")
    status_data = None

    running_pid = is_daemon_running()
    if running_pid:
        print(f"  Daemon Process: Running (PID: {running_pid} from {SELF_HEAL_PID_FILE})")
        if os.path.exists(status_file_path):
            try:
                with open(status_file_path, "r") as f:
                    status_data = json.load(f)

                print(f"  Last Status Update: {datetime.datetime.fromtimestamp(status_data.get('last_updated_ts', 0)).strftime('%Y-%m-%d %H:%M:%S') if status_data.get('last_updated_ts') else 'N/A'}")
                print(f"  Daemon Reported Status: {status_data.get('daemon_status', 'N/A')}")

                print("\n  Monitored Targets Status:")
                targets_status = status_data.get("monitored_targets_status", {})
                if targets_status:
                    for target_id, ts_data in targets_status.items():
                        status_indicator = ts_data.get('status', 'unknown').upper()
                        details = ts_data.get('details', '')
                        # Basic color coding for status (requires a library like 'colorama' or direct ANSI codes)
                        # Simple text based for now:
                        print(f"    - {target_id}: {status_indicator} ({details})")
                else:
                    print("    No target status data available.")

                print("\n  Active Issues Summary:")
                active_issues = status_data.get("active_issues_summary", [])
                print(f"    Total Active Issues: {status_data.get('active_issues_count', len(active_issues))}")
                if active_issues:
                    for issue in active_issues[:3]: # Show top 3
                        print(f"    - Key: {issue.get('key')}, Attempts: {issue.get('attempts', 'N/A')}")
                else:
                    print("    No active issues reported.")

                print("\n  Recent Recovery Actions:")
                recovery_actions = status_data.get("recent_recovery_actions", [])
                if recovery_actions:
                    for action in recovery_actions[-3:]: # Show last 3
                        ts = datetime.datetime.fromtimestamp(action.get('timestamp',0)).strftime('%Y-%m-%d %H:%M:%S') if action.get('timestamp') else 'N/A'
                        print(f"    - [{ts}] Target: {action.get('target_id')}, Action: {action.get('action')}, Outcome: {action.get('outcome')}")
                else:
                    print("    No recent recovery actions reported.")

            except json.JSONDecodeError:
                print(f"  Error: Could not parse status file: {status_file_path}. It might be corrupted.")
            except IOError as e:
                print(f"  Error: Could not read status file {status_file_path}: {e}")
        else:
            print(f"  Status file not found: {status_file_path}. Daemon might be starting or status not yet written.")
    else:
        if os.path.exists(SELF_HEAL_PID_FILE):
            print(f"  Daemon Process: Not Running (Stale PID file found: {SELF_HEAL_PID_FILE})")
        else:
            print("  Daemon Process: Not Running")

    print("\n  Recent Raw Activity (last 5 lines from self_healing.log):")
    log_file = os.path.join(PROJECT_ROOT, "logs", "self_healing.log")
    if os.path.exists(log_file):
        try:
            with open(log_file, "r") as f:
                lines = f.readlines()
                # Print last 5 lines
                for line in lines[-5:]:
                    print(f"    {line.strip()}")
                if not lines:
                    print("    Log file is empty.")
        except Exception as e:
            print(f"    Could not read log file {log_file}: {e}")
    else:
        print(f"    Log file not found: {log_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Katana AI Concierge Command Line Interface.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    subparsers = parser.add_subparsers(title="Available Commands", dest="command", metavar="<command>")
    subparsers.required = True # Make selecting a command mandatory

    # --- Self-Heal command group ---
    sh_parser = subparsers.add_parser(
        "self-heal",
        help="Manage Katana's automated self-healing system.",
        description=(
            "The 'self-heal' command group allows you to control and observe the Katana Self-Healing Daemon.\n"
            "This daemon monitors Katana's core components and attempts to automatically recover from detected issues."
        ),
        formatter_class=argparse.RawTextHelpFormatter # Allows newlines in description
    )
    sh_subparsers = sh_parser.add_subparsers(title="Self-Heal Actions", dest="sh_action", metavar="<action>")
    sh_subparsers.required = True

    # `self-heal run` subcommand
    sh_run_parser = sh_subparsers.add_parser(
        "run",
        help="Start the Katana Self-Healing Daemon.",
        description=(
            "Attempts to start the Self-Healing Daemon in the background.\n"
            "The daemon will then periodically monitor system health, diagnose problems,\n"
            "and attempt automated recovery actions.\n"
            "Note: True daemonization is currently a placeholder; this command sets up the structure."
        ),
        formatter_class=argparse.RawTextHelpFormatter
    )
    sh_run_parser.set_defaults(func=handle_self_heal_run)

    # `self-heal status` subcommand
    sh_status_parser = sh_subparsers.add_parser(
        "status",
        help="Show the current status of the Katana Self-Healing system.",
        description=(
            "Displays the operational status of the Self-Healing Daemon, including:\n"
            "  - Whether the daemon process is running.\n"
            "  - The last reported status from the daemon (via a status file).\n"
            "  - Health of monitored targets (e.g., API, main process).\n"
            "  - Summary of active issues and recent recovery attempts.\n"
            "  - Recent raw log entries from the self-healing module."
        ),
        formatter_class=argparse.RawTextHelpFormatter
    )
    sh_status_parser.set_defaults(func=handle_self_heal_status)

    # --- (Future: Add other top-level commands like 'agent', 'config', etc.) ---

    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        # This case should not be reached if subparsers.required = True for sh_subparsers
        # and for the main parser's subparsers.
        parser.print_help()


if __name__ == "__main__":
    main()
