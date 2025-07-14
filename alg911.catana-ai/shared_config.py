import os
import datetime

# --- Base Directory ---
# Assumes this config file is within the 'alg911.catana-ai' directory.
# All paths will be relative to this base directory.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- File Paths ---
# Centralized definitions for important file paths
COMMANDS_FILE_PATH = os.path.join(BASE_DIR, "katana.commands.json")
MEMORY_FILE_PATH = os.path.join(BASE_DIR, "katana_memory.json")
HISTORY_FILE_PATH = os.path.join(BASE_DIR, "katana.history.json")
EVENTS_LOG_FILE_PATH = os.path.join(BASE_DIR, "katana_events.log")
SYNC_STATUS_FILE_PATH = os.path.join(BASE_DIR, "sync_status.json")

# --- Agent/API Configuration ---
TRADER_API_HOST = "0.0.0.0"
TRADER_API_PORT = 5001  # Port for the Trader API Flask app

AGENT_LOG_PREFIX = "[KatanaAgent_MCP_v1]"  # Default log prefix for the main agent


# --- Logging Function (Shared) ---
# A simple shared logging function.
# More sophisticated logging (e.g., using Python's logging module) could be implemented here.
def log_event(event_message, level="info", component_prefix="SHARED_CONFIG"):
    """
    Logs an event message to the EVENTS_LOG_FILE_PATH.
    Prepends timestamp, level, and component prefix.
    """
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    log_entry_line = (
        f"[{timestamp}] {level.upper()}: [{component_prefix}] {event_message}\n"
    )

    try:
        log_dir = os.path.dirname(EVENTS_LOG_FILE_PATH)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        with open(EVENTS_LOG_FILE_PATH, "a") as f:
            f.write(log_entry_line)

    except Exception as e:
        # Fallback to print if logging to file fails
        print(
            f"CRITICAL_LOG_FAILURE (logged from shared_config): {log_entry_line} (Error: {e})"
        )


# --- Example Usage (for testing this file directly) ---
if __name__ == "__main__":
    print(f"Base Directory: {BASE_DIR}")
    print(f"Commands File Path: {COMMANDS_FILE_PATH}")
    print(f"Events Log File Path: {EVENTS_LOG_FILE_PATH}")

    # Test logging
    log_event("Shared config initialized.", "info", "ConfigTest")
    log_event("This is a debug message from shared_config test.", "debug", "ConfigTest")

    # Verify that trader_api.py can now import this
    try:
        import trader_api

        # If trader_api.py used shared_config.log_event, that would be a good test too.
        # For now, just check if it can resolve COMMANDS_FILE correctly.
        if trader_api.COMMANDS_FILE == COMMANDS_FILE_PATH:
            print(
                "trader_api.COMMANDS_FILE successfully uses shared_config.COMMANDS_FILE_PATH."
            )
            log_event(
                "trader_api.COMMANDS_FILE linkage to shared_config verified.",
                "info",
                "ConfigTest",
            )
        else:
            print(
                f"ERROR: trader_api.COMMANDS_FILE ({trader_api.COMMANDS_FILE}) is different from shared_config.COMMANDS_FILE_PATH ({COMMANDS_FILE_PATH})."
            )
            log_event(
                "Mismatch in COMMANDS_FILE path between trader_api and shared_config.",
                "error",
                "ConfigTest",
            )
    except ImportError:
        print("Could not import trader_api.py to test shared_config linkage.")
        log_event(
            "Could not import trader_api.py for config linkage test.",
            "warning",
            "ConfigTest",
        )
    except AttributeError:
        print(
            "trader_api.py does not have COMMANDS_FILE attribute or it's not yet updated to use shared_config."
        )
        log_event(
            "trader_api.COMMANDS_FILE attribute issue for config linkage test.",
            "warning",
            "ConfigTest",
        )

    print("Shared config test complete. Check katana_events.log for messages.")
