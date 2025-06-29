import os
import json
import time
from datetime import datetime
from katana.decorators.trace_command import trace_command # Import the decorator

TRADER_PID_FILE = "/tmp/katana_trader.pid"
TRADER_STATUS_FILE = "/tmp/katana_trader_status.json"

def _read_pid_file():
    try:
        with open(TRADER_PID_FILE, "r") as f:
            return int(f.read().strip())
    except FileNotFoundError:
        return None
    except ValueError:
        print(f"Error: PID file {TRADER_PID_FILE} contains invalid data.")
        # Consider renaming corrupted PID file as in self_heal.py
        return None

def _write_pid_file():
    pid = os.getpid() # In a real scenario, this would be the trader process PID
    try:
        with open(TRADER_PID_FILE, "w") as f:
            f.write(str(pid))
        print(f"Trader PID file {TRADER_PID_FILE} created for PID {pid}.")
    except IOError as e:
        print(f"Error: Unable to write PID file {TRADER_PID_FILE}. {e}")
        return False
    return True

def _remove_pid_file():
    try:
        if os.path.exists(TRADER_PID_FILE):
            os.remove(TRADER_PID_FILE)
            print(f"Trader PID file {TRADER_PID_FILE} removed.")
    except IOError as e:
        print(f"Warning: Unable to remove PID file {TRADER_PID_FILE}. {e}")

def _update_status_file(status_data):
    try:
        with open(TRADER_STATUS_FILE, "w") as f:
            json.dump(status_data, f, indent=2)
        # print(f"Trader status file {TRADER_STATUS_FILE} updated.")
    except IOError as e:
        print(f"Error writing status to {TRADER_STATUS_FILE}: {e}")

# Note: _read_status_file, _write_pid_file etc. are internal helpers, not commands.
# No telemetry needed for them unless explicitly desired for deep debugging.

def _read_status_file():
    try:
        with open(TRADER_STATUS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not parse status file {TRADER_STATUS_FILE}. It might be corrupted.")
        return None
    except IOError as e:
        print(f"Error: Could not read status file {TRADER_STATUS_FILE}. {e}")
        return None

@trace_command
def start_trader(args):
    print("Attempting to start Katana Trader...")
    pid = _read_pid_file()
    if pid:
        # Check if the process is actually running (simplified check)
        if os.path.exists(f"/proc/{pid}"): # Basic check for Unix-like systems
            print(f"Katana Trader is already running with PID {pid} (according to {TRADER_PID_FILE}).")
            return
        else:
            print(f"Warning: Stale PID file found for PID {pid}. Process not running. Overwriting.")

    if not _write_pid_file(): # This will use the current CLI process PID for simplicity
        return

    # Simulate trader process PID (using current process PID for this CLI command)
    trader_pid = os.getpid()

    status_data = {
        "status": "active",
        "pid": trader_pid,
        "start_time": time.time(),
        "exchange": "SimulatedExchange", # Placeholder
        "strategy": "DefaultStrategy",   # Placeholder
        "balance": {"USD": 10000, "BTC": 0.5} # Placeholder
    }
    _update_status_file(status_data)
    print(f"Katana Trader started successfully (Simulated PID: {trader_pid}).")
    print(f"Exchange: {status_data['exchange']}, Strategy: {status_data['strategy']}")

@trace_command
def get_trader_status(args):
    print("Getting Katana Trader status...")
    pid = _read_pid_file()
    status_data = _read_status_file()

    if not pid and not status_data:
        print("Katana Trader is not running (no PID file or status file found).")
        return

    if not status_data: # PID file exists but no status file
        if pid:
             print(f"Katana Trader PID file found (PID: {pid}), but status file is missing.")
             print("Trader might be in an inconsistent state or starting up.")
        # This case is already covered by the first check, but good for clarity.
        return

    # If status_data exists, use it as the primary source of truth.
    # Cross-check with PID file.

    reported_status = status_data.get("status", "unknown")
    reported_pid = status_data.get("pid")

    print(f"Status from file: {reported_status.capitalize()}")

    if reported_pid:
        print(f"  Reported PID: {reported_pid}")
        if pid and pid != reported_pid:
            print(f"  Warning: PID in status file ({reported_pid}) differs from PID in {TRADER_PID_FILE} ({pid}).")
        elif not pid and reported_status == "active":
             print(f"  Warning: Status is 'active' but PID file {TRADER_PID_FILE} is missing.")

        # Simple check if process is alive (for Unix-like systems)
        if os.path.exists(f"/proc/{reported_pid}"):
            print(f"  Process {reported_pid} appears to be running.")
        elif reported_status == "active":
            print(f"  Warning: Process {reported_pid} is NOT running, but status is 'active'. Stale status file?")

    elif reported_status == "active": # Status is active but no PID in status file
        print("  Warning: Status is 'active' but no PID is recorded in the status file.")


    start_time_ts = status_data.get("start_time")
    if start_time_ts:
        try:
            start_dt = datetime.fromtimestamp(start_time_ts)
            uptime_seconds = (datetime.now() - start_dt).total_seconds()
            print(f"  Start Time: {start_dt.strftime('%Y-%m-%d %H:%M:%S')} (Uptime: {uptime_seconds:.0f}s)")
        except Exception as e:
            print(f"  Could not parse start_time: {e}")

    if "exchange" in status_data:
        print(f"  Exchange: {status_data['exchange']}")
    if "strategy" in status_data:
        print(f"  Strategy: {status_data['strategy']}")
    if "balance" in status_data:
        print(f"  Balance: {json.dumps(status_data['balance'])}")

    if reported_status == "stopped" and "stop_time" in status_data:
        try:
            stop_dt = datetime.fromtimestamp(status_data['stop_time'])
            print(f"  Stop Time: {stop_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            print(f"  Could not parse stop_time: {e}")


@trace_command
def stop_trader(args):
    print("Attempting to stop Katana Trader...")
    pid = _read_pid_file()
    status_data = _read_status_file()

    if not pid and (not status_data or status_data.get("status") != "active"):
        print("Katana Trader does not appear to be running (no active PID or status).")
        return

    # Simulate stopping the process
    # In a real app, you'd use the PID to send a signal (e.g., SIGTERM)
    if pid:
        print(f"Simulating sending stop signal to trader process {pid}...")
        # os.kill(pid, signal.SIGTERM) # This would be the real command
        _remove_pid_file() # Remove PID file as part of stopping
    else:
        print("No PID file found, but status file might indicate it was active.")


    if status_data:
        status_data["status"] = "stopped"
        status_data["stop_time"] = time.time()
        # Optionally clear or keep other fields like pid, balance, etc.
        # For now, we keep them to show the state when it was stopped.
        _update_status_file(status_data)
    else:
        # If no status file, create one to indicate it's stopped.
        _update_status_file({
            "status": "stopped",
            "stop_time": time.time(),
            "notes": "Trader was stopped; no previous status file found."
        })

    print("Katana Trader stopped successfully (Simulated).")

@trace_command
def reset_trader(args):
    """
    Resets the trader to a default state.
    For now, this is a placeholder and simulates a reset action.
    It will stop the trader if running and clear status.
    """
    print("Attempting to reset Katana Trader...")

    # First, try to stop the trader if it's running
    pid = _read_pid_file()
    status_data = _read_status_file()

    if pid or (status_data and status_data.get("status") == "active"):
        print("Trader appears to be running or active, stopping it first...")
        stop_trader(args) # Call existing stop_trader function
    else:
        print("Trader is not running. Proceeding with reset.")

    # Clear status file content beyond just "stopped"
    if os.path.exists(TRADER_STATUS_FILE):
        print(f"Clearing trader status file: {TRADER_STATUS_FILE}")
        _update_status_file({
            "status": "reset",
            "reset_time": time.time(),
            "notes": "Trader has been reset."
        })

    # Ensure PID file is removed if stop_trader didn't catch it (e.g., if only status file existed)
    if os.path.exists(TRADER_PID_FILE):
        _remove_pid_file()

    print("Katana Trader reset successfully (Simulated).")
    return {"status": "reset_complete", "message": "Trader reset to default state."}

if __name__ == '__main__':
    # Basic testing (not part of the CLI integration yet)
    class Args: pass
    args = Args()

    # Test start
    start_trader(args)
    print("\n--- Status after start ---")
    get_trader_status(args)

    # Test stop
    print("\n--- Stopping ---")
    stop_trader(args)
    print("\n--- Status after stop ---")
    get_trader_status(args)

    # Test status when stopped
    print("\n--- Status again (should be stopped) ---")
    get_trader_status(args)

    # Test starting again
    print("\n--- Starting again ---")
    start_trader(args)
    print("\n--- Status after restart ---")
    get_trader_status(args)

    # Clean up
    if os.path.exists(TRADER_PID_FILE): os.remove(TRADER_PID_FILE)
    if os.path.exists(TRADER_STATUS_FILE): os.remove(TRADER_STATUS_FILE)
