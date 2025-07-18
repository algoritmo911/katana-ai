import os
import sys
import time
import atexit
import signal
import json  # For status file later
from datetime import datetime  # For status output
import traceback  # For logging tracebacks
from katana.decorators.trace_command import trace_command  # Import the decorator

# Attempt to import post_task_verifier, handle if it's not found during development phases
try:
    from katana import post_task_verifier
except ImportError:
    # This allows self_heal to potentially run or be imported even if post_task_verifier is missing,
    # though verification features would be disabled.
    # Consider if a hard failure is better if post_task_verifier is essential.
    print(
        "Warning: katana.post_task_verifier module not found. Task verification will be skipped.",
        file=sys.stderr,
    )
    post_task_verifier = None


PID_FILE = "/tmp/katana_self_heal.pid"
STATUS_FILE = "/tmp/self_healing_status.json"
LOG_FILE = "/tmp/katana_self_heal.log"
KATANA_RESULT_JSON = "/tmp/katana_result.json"  # Default path for verification results

MAX_RESTART_ATTEMPTS = 3
RESTART_DELAY_SECONDS = 10  # Wait 10 seconds before restarting


# Configure basic logging for the daemon process
def setup_daemon_logging():
    sys.stdout.flush()
    sys.stderr.flush()
    try:
        dn = open(os.devnull, "r")
        os.dup2(dn.fileno(), sys.stdin.fileno())
        dn.close()
    except FileNotFoundError:
        sys.stderr.write(
            "Warning: os.devnull not found, stdin may not be fully detached.\n"
        )
    except OSError as e:
        sys.stderr.write(f"Warning: Error with os.devnull for stdin: {e}\n")

    try:
        # Ensure log directory exists (useful if LOG_FILE is in a subdirectory)
        log_dir = os.path.dirname(LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        so = open(LOG_FILE, "a+")
        se = open(LOG_FILE, "a+")
    except IOError as e:
        sys.stderr.write(
            f"Fatal: Could not open log file {LOG_FILE} for writing: {e}\n"
        )
        sys.exit(1)

    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())
    # Keep so, se alive by making them part of a global or passed object if necessary,
    # though for simple redirection, dup2 is usually sufficient.


def write_pid_file():
    pid = os.getpid()
    try:
        with open(PID_FILE, "w") as f:
            f.write(str(pid))
        atexit.register(remove_pid_file)
        print(f"Daemon active with PID {pid}. PID file {PID_FILE} created.")
    except IOError as e:
        print(f"Error: Unable to write PID file {PID_FILE}. {e}", file=sys.stderr)
        sys.exit(1)


def remove_pid_file():
    try:
        if os.path.exists(PID_FILE):
            current_pid_in_file = None
            try:
                with open(PID_FILE, "r") as f:
                    current_pid_in_file = int(f.read().strip())
            except Exception:
                pass

            if current_pid_in_file is None or current_pid_in_file == os.getpid():
                os.remove(PID_FILE)
                print(f"PID file {PID_FILE} removed by process {os.getpid()}.")
            else:
                print(
                    f"PID file {PID_FILE} (PID {current_pid_in_file}) not removed by process {os.getpid()} as it seems to belong to another process."
                )
    except IOError as e:
        print(f"Warning: Unable to remove PID file {PID_FILE}. {e}", file=sys.stderr)
    except Exception as e:
        print(f"Unexpected error removing PID file {PID_FILE}: {e}", file=sys.stderr)


def read_pid_file():
    try:
        with open(PID_FILE, "r") as f:
            return int(f.read().strip())
    except FileNotFoundError:
        return None
    except ValueError:
        sys.stderr.write(f"Error: PID file {PID_FILE} contains invalid data.\n")
        try:
            corrupt_path = (
                PID_FILE + ".corrupt_" + datetime.now().strftime("%Y%m%d%H%M%S")
            )
            os.rename(PID_FILE, corrupt_path)
            sys.stderr.write(f"Renamed corrupted PID file to {corrupt_path}\n")
        except OSError as e:
            sys.stderr.write(f"Could not rename corrupted PID file: {e}\n")
        return None


def _update_status_file_internal(status_dict_to_write, is_crash_update=False):
    """Internal helper to write status, used by daemon loop and signal handlers."""
    try:
        # Ensure essential fields exist if updating due to crash/signal
        if is_crash_update:
            status_dict_to_write.setdefault("pid", os.getpid())
            status_dict_to_write.setdefault("last_updated", time.time())

        with open(STATUS_FILE, "w") as f_status:
            json.dump(status_dict_to_write, f_status, indent=2)
        if (
            not is_crash_update
        ):  # Avoid logging during critical shutdown/crash status update
            # This print goes to daemon log
            pass  # print(f"Status file {STATUS_FILE} updated.") # Can be too verbose
    except Exception as e_status_write:
        # This print goes to daemon log. If it's a crash update, this might be the last log.
        print(f"Daemon error writing status to {STATUS_FILE}: {e_status_write}")
        if not is_crash_update:  # Avoid modifying dict if it's already a crash dict
            status_dict_to_write.setdefault("warnings", []).append(
                [time.time(), f"Failed to write status to file: {e_status_write}"]
            )
            status_dict_to_write["warnings"] = status_dict_to_write["warnings"][-5:]


health_status_global = {}  # Global-like dict for the daemon's current status


def daemon_main_loop():
    # Use and update health_status_global
    global health_status_global

    print(
        f"Daemon process (PID: {os.getpid()}) main loop started. Current status: {health_status_global.get('status')}"
    )

    # Initialize if empty or if restarting (started_at should persist across internal restarts)
    health_status_global.setdefault("pid", os.getpid())
    health_status_global.setdefault(
        "started_at", time.time()
    )  # This remains from the very first start
    health_status_global.setdefault("checks", [])
    health_status_global.setdefault("warnings", [])
    health_status_global["status"] = "running"
    health_status_global["last_updated"] = time.time()
    health_status_global["current_loop_restarted_at"] = (
        time.time()
    )  # Timestamp for this specific main_loop instance

    _update_status_file_internal(health_status_global)
    # print("Initial status for this main loop iteration written.") # Can be verbose

    # Define a list of task IDs to cycle through for verification
    # These should match keys in DUMMY_TASK_EXPECTATIONS in post_task_verifier.py
    simulated_task_ids = [
        "create_config_file",  # Will fail first, then succeed after simulated fix
        "run_migrations",
        "start_server",
        "successful_task",
        "unknown_task_force_fail",  # Example of a task that fails verification
    ]
    task_id_index = 0

    loop_count = 0
    while True:  # This is the core operational loop
        loop_count += 1
        print(f"Daemon main loop iteration: {loop_count}")

        health_status_global["last_updated"] = time.time()
        # health_status_global["status"] = "running" # Already set at loop start

        avg_load = os.getloadavg() if hasattr(os, "getloadavg") else (0, 0, 0)
        current_check = {
            "timestamp": time.time(),
            "check_name": "system_resource_check",
            "result": "ok",
            "details": {
                "cpu_load_1m": round(avg_load[0], 2),
                "loop_count_this_instance": loop_count,
            },
        }
        health_status_global["checks"].append(current_check)
        health_status_global["checks"] = health_status_global["checks"][
            -10:
        ]  # Keep last 10 checks

        # --- SIMULATED TASK EXECUTION ---
        print(f"Simulating execution of a task in loop iteration {loop_count}...")
        # This is where actual task logic would go.
        # For now, we just wait. The important part is the verification that follows.

        # --- POST-TASK VERIFICATION ---
        if post_task_verifier:
            current_task_id = simulated_task_ids[
                task_id_index % len(simulated_task_ids)
            ]
            print(f"Attempting to verify simulated task: {current_task_id}")

            # Special handling for 'create_config_file' to demonstrate success after failure
            if current_task_id == "create_config_file":
                config_file_path = post_task_verifier.DUMMY_TASK_EXPECTATIONS[
                    "create_config_file"
                ]["filepath"]
                # On the first attempt for this task ID (or if file doesn't exist), it should fail.
                # On subsequent attempts for this task ID, simulate the file has been created.
                # We use loop_count to make this behavior change over time if this task_id is hit multiple times.
                # A more robust way would be to track attempts per task_id if the daemon is long-running.
                # For simplicity, let's say if loop_count is even it exists, if odd it does not.
                # This is just for daemon demonstration, manual verify will test more directly.
                if loop_count % 2 == 0:  # Simulate file exists on even loops
                    if not os.path.exists(config_file_path):
                        print(
                            f"Simulating creation of {config_file_path} for verification success."
                        )
                        with open(config_file_path, "w") as f:
                            f.write("SIMULATED_CONTENT=true")
                else:  # Simulate file missing on odd loops
                    if os.path.exists(config_file_path):
                        print(
                            f"Simulating removal of {config_file_path} for verification failure."
                        )
                        os.remove(config_file_path)

            if current_task_id == "run_migrations":
                log_file_path = post_task_verifier.DUMMY_TASK_EXPECTATIONS[
                    "run_migrations"
                ]["log_file"]
                # Clean up log from previous run of this task to ensure clean test
                if os.path.exists(log_file_path):
                    os.remove(log_file_path)

            verification_result = post_task_verifier.verify_task(current_task_id)
            post_task_verifier.write_katana_result(
                verification_result, KATANA_RESULT_JSON
            )

            print(
                f"Verification result for task '{current_task_id}': {verification_result.get('status')}"
            )
            if verification_result.get("status") == "failure":
                print(f"  Reason: {verification_result.get('reason')}")
                print(f"  Fix: {verification_result.get('fix_suggestion')}")

            # Add verification result to daemon status
            health_status_global.setdefault("last_task_verifications", []).append(
                verification_result
            )
            health_status_global["last_task_verifications"] = health_status_global[
                "last_task_verifications"
            ][
                -5:
            ]  # Keep last 5

            task_id_index += 1  # Move to next task for next iteration
        else:
            print(
                "Task verification skipped as post_task_verifier module is not available."
            )

        print(f"Finished simulated task and verification for loop {loop_count}.")
        # --- END POST-TASK VERIFICATION ---

        # Example: Simulate a recoverable error to test restart
        # This will trigger after MAX_RESTART_ATTEMPTS + some loops to ensure it's not immediate
        if (
            health_status_global.get("restart_attempts_count", 0) < MAX_RESTART_ATTEMPTS
        ):  # only simulate if restarts are allowed
            # Shorten loop for testing crashes, e.g. crash on 3rd successful loop of this instance
            if (
                loop_count == 3 and not args.no_simulated_crash
            ):  # Added a simple arg flag to disable this for easier testing
                print("Simulating a recoverable error in daemon_main_loop...")
                raise ValueError(
                    f"Simulated recoverable error for restart test (loop {loop_count})"
                )

        _update_status_file_internal(health_status_global)
        # Shorten sleep for faster testing of verification cycling
        print(f"Daemon sleeping for {args.daemon_sleep_interval} seconds...")
        time.sleep(args.daemon_sleep_interval)


def _shutdown_daemon(signal_name_or_reason):
    global health_status_global
    print(
        f"Shutdown initiated by '{signal_name_or_reason}'. Daemon (PID: {os.getpid()}) initiating shutdown..."
    )

    health_status_global["status"] = f"shutting_down ({signal_name_or_reason})"
    health_status_global["last_updated"] = time.time()
    health_status_global.setdefault("warnings", []).append(
        [time.time(), f"Shutdown initiated by {signal_name_or_reason}."]
    )
    _update_status_file_internal(health_status_global, is_crash_update=True)

    print("Daemon shutdown sequence complete.")
    sys.exit(0)


def sigterm_handler(signum, frame):
    _shutdown_daemon(signal.Signals(signum).name)


def sigint_handler(signum, frame):
    _shutdown_daemon(signal.Signals(signum).name)


def sighup_handler(signum, frame):
    global health_status_global
    print(
        f"SIGHUP received. Daemon (PID: {os.getpid()}) reloading configuration (simulated)..."
    )

    health_status_global["status"] = "reloading_config (simulated)"
    health_status_global["last_updated"] = time.time()
    health_status_global.setdefault("warnings", []).append(
        [time.time(), "SIGHUP received, configuration reload simulated."]
    )
    _update_status_file_internal(health_status_global)
    print("SIGHUP handling complete (simulated reload).")


@trace_command
def run_daemon(args):
    global health_status_global
    # CLI-facing messages before daemonization
    print("Attempting to start self-healing daemon...")

    pid_from_file = read_pid_file()
    if pid_from_file:
        try:
            os.kill(pid_from_file, 0)
            print(
                f"Error: Daemon already running with PID {pid_from_file} (from {PID_FILE})."
            )
            sys.exit(1)
        except ProcessLookupError:
            print(
                f"Warning: Stale PID file found ({PID_FILE} for PID {pid_from_file}, process not running). Removing it."
            )
            try:
                os.remove(PID_FILE)
                print(f"Stale PID file {PID_FILE} removed successfully.")
            except OSError as e_remove:
                print(
                    f"Error removing stale PID file {PID_FILE}: {e_remove}. Please remove it manually.",
                    file=sys.stderr,
                )
                sys.exit(1)
        except PermissionError:
            print(
                f"Error: Daemon process with PID {pid_from_file} is running, but you don't have permission to signal it.",
                file=sys.stderr,
            )
            sys.exit(1)
        except Exception as e_kill:
            print(
                f"Error checking status of existing PID {pid_from_file}: {e_kill}",
                file=sys.stderr,
            )
            sys.exit(1)

    try:
        child_pid1 = os.fork()
        if child_pid1 > 0:
            time.sleep(0.3)  # Increased sleep slightly
            try:
                wait_pid, status = os.waitpid(child_pid1, os.WNOHANG)
                if wait_pid == child_pid1:
                    if os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0:
                        print(
                            "Daemon process setup initiated successfully in background."
                        )
                    else:  # Intermediate process exited with error
                        print(
                            f"Error: Daemon setup process (PID: {child_pid1}) exited with status {os.WEXITSTATUS(status)}.",
                            file=sys.stderr,
                        )
                        print(
                            "Daemon may not have started. Check logs if any (e.g. /tmp/katana_self_heal.log).",
                            file=sys.stderr,
                        )
                        sys.exit(1)
                # else: intermediate process still running, this is fine.
            except ChildProcessError:
                print(
                    "Warning: No child process found after first fork (unexpected), but continuing.",
                    file=sys.stderr,
                )
            except OSError as e_wait:
                print(
                    f"Warning: Error waiting for first fork child: {e_wait}",
                    file=sys.stderr,
                )
            sys.exit(0)
    except OSError as e_fork1:
        print(f"Fork #1 failed: {e_fork1.errno} ({e_fork1.strerror})", file=sys.stderr)
        sys.exit(1)

    # os.chdir("/") # Optional: Change working directory. Consider implications for relative paths.
    os.setsid()
    os.umask(0)

    try:
        child_pid2 = os.fork()
        if child_pid2 > 0:
            sys.exit(0)  # Second parent (child of first fork) exits.
    except OSError as e_fork2:
        # This error occurs in the child of the first fork. Hard to report to original user.
        # If logging were set up *before* this, it could log here.
        # For now, write to stderr, though it might be detached.
        sys.stderr.write(f"Fork #2 failed: {e_fork2.errno} ({e_fork2.strerror})\n")
        sys.exit(1)  # Exit with error, daemon will not start.

    # Actual Daemon Process Starts Here (grandchild of original process)
    setup_daemon_logging()  # From now on, print() goes to LOG_FILE
    print(
        f"Daemon process starting. PID: {os.getpid()}, PPID: {os.getppid()}, SID: {os.getsid(0)}"
    )
    write_pid_file()  # Creates PID_FILE and registers atexit handler for its removal

    signal.signal(signal.SIGTERM, sigterm_handler)
    signal.signal(signal.SIGHUP, sighup_handler)
    signal.signal(signal.SIGINT, sigint_handler)
    print("Signal handlers registered.")

    # Store args for use in daemon_main_loop if needed
    # This is a bit of a hack; proper daemons might pass config objects.
    # For now, to control sleep interval and crash simulation from CLI:
    run_daemon.args = args

    # Initialize health_status_global for the very first run
    health_status_global = {
        "pid": os.getpid(),
        "started_at": time.time(),  # This is the true start time of the daemon process
        "status": "initializing",
        "restart_attempts_count": 0,
        "checks": [],
        "warnings": [],
        "last_task_verifications": [],
    }
    _update_status_file_internal(health_status_global)  # Initial status write

    restart_attempts_done = 0
    while restart_attempts_done <= MAX_RESTART_ATTEMPTS:
        health_status_global["status"] = "main_loop_starting"
        health_status_global["last_updated"] = time.time()
        health_status_global["current_main_loop_attempt_count"] = restart_attempts_done

        if restart_attempts_done > 0:
            print(
                f"--- Daemon Main Loop: Attempting restart {restart_attempts_done}/{MAX_RESTART_ATTEMPTS} after {RESTART_DELAY_SECONDS} seconds ---"
            )
            health_status_global["status"] = (
                f"restarting_main_loop (attempt {restart_attempts_done})"
            )
            _update_status_file_internal(health_status_global)
            time.sleep(RESTART_DELAY_SECONDS)
            print(f"Daemon process (PID: {os.getpid()}) main loop restarting.")

        print(f"Starting daemon main loop (Overall attempt {restart_attempts_done})...")
        try:
            # Pass the args to daemon_main_loop
            daemon_main_loop(args)  # This is the blocking call to the daemon's work
            # If daemon_main_loop returns, it implies a controlled shutdown from within itself.
            print("Daemon main loop returned cleanly. Initiating shutdown.")
            _shutdown_daemon("main_loop_returned")
            break  # Exit the while restart_attempts_done loop
        except SystemExit as e_sysexit:
            # This is typically raised by _shutdown_daemon() after a signal.
            print(
                f"SystemExit caught in run_daemon's loop ({e_sysexit.code}). Daemon is exiting."
            )
            raise  # Re-raise to ensure atexit handlers run and process terminates
        except Exception as e_mainloop:
            # An unexpected error occurred within daemon_main_loop()
            restart_attempts_done += 1  # Increment before using in messages/status
            health_status_global["restart_attempts_count"] = restart_attempts_done

            print(
                f"ERROR: Unhandled exception in daemon main loop (Crash number {restart_attempts_done}): {e_mainloop}",
                file=sys.stderr,
            )
            trace_info = traceback.format_exc()
            print(f"Traceback:\n{trace_info}", file=sys.stderr)

            health_status_global["status"] = (
                f"crashed_attempting_restart (after crash {restart_attempts_done})"
            )
            health_status_global["error"] = str(e_mainloop)
            health_status_global["last_updated"] = time.time()
            health_status_global["traceback_snippet"] = trace_info.splitlines()[
                -5:
            ]  # Store last 5 lines
            _update_status_file_internal(health_status_global, is_crash_update=True)
            print("Status file updated to reflect crash and pending restart.")

            if restart_attempts_done > MAX_RESTART_ATTEMPTS:
                print(
                    f"FATAL: Maximum main loop restart attempts ({MAX_RESTART_ATTEMPTS}) reached. Daemon will now exit."
                )
                health_status_global["status"] = "crashed_max_restarts_exceeded"
                health_status_global["error"] = str(e_mainloop)  # Keep last error
                health_status_global["traceback"] = (
                    trace_info.splitlines()
                )  # Store full traceback for final crash
                _update_status_file_internal(health_status_global, is_crash_update=True)
                sys.exit(1)  # Exit daemon process after max retries
        else:
            # This 'else' belongs to the 'try...except' for daemon_main_loop()
            # It executes if no exception occurred in daemon_main_loop, meaning it returned.
            print(
                "Daemon main loop finished without error (returned). This implies a controlled stop."
            )
            _shutdown_daemon("main_loop_completed_normally")
            break  # Exit the while restart_attempts_done loop

    print("Daemon run_daemon function is concluding.")


@trace_command
def get_status(args):
    # Output of this function goes to the CLI user's console.
    print("Getting self-healing daemon status...")
    pid_from_file = read_pid_file()

    daemon_is_confirmed_running = False
    if pid_from_file:
        try:
            os.kill(pid_from_file, 0)
            print(
                f"System reports process with PID {pid_from_file} (from {PID_FILE}) is alive."
            )
            daemon_is_confirmed_running = True
        except ProcessLookupError:
            print(
                f"System reports process with PID {pid_from_file} (from {PID_FILE}) is NOT running."
            )
        except PermissionError:
            print(
                f"Process with PID {pid_from_file} (from {PID_FILE}) is running, but you lack permissions to send signals."
            )
            daemon_is_confirmed_running = True
        except OSError as e_kill_check:
            print(
                f"Error checking daemon process PID {pid_from_file} via kill: {e_kill_check}. PID file might be stale."
            )
    else:
        print(
            f"Daemon PID file ({PID_FILE}) not found or invalid. Daemon is likely not running."
        )

    if not os.path.exists(STATUS_FILE):
        if daemon_is_confirmed_running:
            print(
                f"Status file {STATUS_FILE} not found, but a process with PID {pid_from_file} is active."
            )
            print(
                "Daemon might be initializing, status file path misconfigured, or not yet written."
            )
        else:
            print(
                f"Status file {STATUS_FILE} not found. No active daemon PID detected."
            )
        return

    print(f"\n--- Reading Status from {STATUS_FILE} ---")
    try:
        with open(STATUS_FILE, "r") as f_status_read:
            status_data = json.load(f_status_read)

        print(json.dumps(status_data, indent=2, sort_keys=True))

        reported_pid_in_status = status_data.get("pid")
        if (
            pid_from_file
            and reported_pid_in_status
            and reported_pid_in_status != pid_from_file
        ):
            print(
                f"\nWARNING: PID in status file ({reported_pid_in_status}) does not match PID in PID file ({pid_from_file}). This may indicate an inconsistency."
            )
        elif not pid_from_file and reported_pid_in_status:
            print(
                f"\nINFO: Status file contains PID {reported_pid_in_status}, but no active PID file was found (or PID file was invalid)."
            )

        timestamp = status_data.get("last_updated")
        if timestamp:
            try:
                dt_object = datetime.fromtimestamp(timestamp)
                last_updated_ago = (datetime.now() - dt_object).total_seconds()
                print(
                    f"\nLast status update: {dt_object.strftime('%Y-%m-%d %H:%M:%S')} ({last_updated_ago:.0f} seconds ago)"
                )
            except Exception as e_ts:
                print(f"\nCould not parse last_updated timestamp '{timestamp}': {e_ts}")

        current_daemon_status_from_file = status_data.get("status", "unknown")
        # Refined conditions for warnings
        non_active_statuses = [
            "shutting_down",
            "crashed",
            "stopped",
            "crashed_max_restarts_exceeded",
            "main_loop_returned",
            "main_loop_completed_normally",
        ]
        if (
            not daemon_is_confirmed_running
            and current_daemon_status_from_file not in non_active_statuses
            and current_daemon_status_from_file != "unknown"
        ):
            print(
                f"\nWARNING: System reports daemon is NOT running, but status file shows an active-like state: '{current_daemon_status_from_file}'. Status file might be stale."
            )
        elif daemon_is_confirmed_running and any(
            s in current_daemon_status_from_file for s in ["crashed", "stopped"]
        ):  # Check substrings for crashed states
            print(
                f"\nWARNING: System reports daemon IS running, but status file indicates a problematic state: '{current_daemon_status_from_file}'. This could be a discrepancy or a very recent issue."
            )

        error_info = status_data.get("error")
        if error_info:
            print(f"\n--- Error Information (from status file) ---")
            print(error_info)
            tb_info = status_data.get("traceback_snippet") or status_data.get(
                "traceback"
            )
            if tb_info and isinstance(tb_info, list):
                print("Traceback snippet/info:")
                for line in tb_info[:10]:
                    print(f"  {line}")

        warnings_list = status_data.get("warnings")
        if warnings_list:
            print("\n--- Recent Warnings (from status file) ---")
            for item in warnings_list:
                if isinstance(item, list) and len(item) == 2:
                    warn_ts, warn_msg = item
                    try:
                        warn_dt = datetime.fromtimestamp(warn_ts)
                        print(
                            f"- At {warn_dt.strftime('%Y-%m-%d %H:%M:%S')}: {warn_msg}"
                        )
                    except Exception:  # Catch broad error for timestamp parsing
                        print(f"- At {warn_ts} (raw timestamp): {warn_msg}")
                else:
                    print(f"- {item} (malformed warning entry)")

    except json.JSONDecodeError:
        print(
            f"Error: Could not parse status file {STATUS_FILE}. It might be corrupted."
        )
        if daemon_is_confirmed_running:
            print("The daemon appears to be running but its status cannot be read.")
    except IOError as e_io_status:
        print(f"Error: Could not read status file {STATUS_FILE}. {e_io_status}")
    except Exception as e_get_status_unexpected:
        print(
            f"An unexpected error occurred while reading status: {e_get_status_unexpected}"
        )
        print(f"Traceback:\n{traceback.format_exc()}")


@trace_command
def simulate_failure_command(args):
    """
    Simulates a failure condition for the self-healing mechanism to detect.
    This command will log a critical error message.
    The self-healing daemon (if running) should pick this up.
    """
    print("Simulating a failure condition for self-heal...")
    # Log a critical error message that the daemon might be configured to detect
    # For demonstration, we'll just print a message to the daemon's log.
    # A more integrated approach would be to write to a specific error file
    # or trigger a condition the daemon actively monitors.

    log_message = f"{datetime.now().isoformat()} - CRITICAL: Simulated failure triggered by CLI command.\n"
    try:
        # Attempt to append to the main daemon log file
        with open(LOG_FILE, "a") as f_log:
            f_log.write(log_message)
        print(f"Simulated critical error written to {LOG_FILE}")
        print(
            "If the self-heal daemon is running and configured to monitor this log, it should react."
        )
    except IOError as e:
        print(f"Error writing simulated failure to log file {LOG_FILE}: {e}")
        print(
            "Please ensure the daemon's log path is accessible or the daemon is running to create it."
        )
    except Exception as e_general:
        print(f"An unexpected error occurred during failure simulation: {e_general}")

    # Additionally, could update status file to 'error' if that's a trigger
    # This is a simplified simulation. A real one might corrupt a file,
    # stop a dependent service, or send a specific signal.
    # For now, logging is a direct way to inject a detectable event.
