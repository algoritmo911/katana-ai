import json
import os
import datetime

# --- File Paths ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KEYS_FILE = os.path.join(SCRIPT_DIR, "katana_keys.json")
EVENTS_LOG_FILE = os.path.join(SCRIPT_DIR, "katana_events.log") # For logging actions
AGENT_LOG_PREFIX = "[KatanaKeyManager]"

# --- Logging (copied and adapted from katana_agent.py for now) ---
# In a larger application, logging might be centralized.
def log_event(event_message, level="info"):
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    log_entry_line = f"[{timestamp}] {level.upper()}: {AGENT_LOG_PREFIX} {event_message}\n"
    try:
        log_dir = os.path.dirname(EVENTS_LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        with open(EVENTS_LOG_FILE, "a") as f:
            f.write(log_entry_line)
    except Exception as e:
        print(f"CRITICAL_LOG_FAILURE: {log_entry_line} (Error: {e})")

# --- JSON File I/O Utilities (copied and adapted from katana_agent.py) ---
def _load_keys_data():
    """Loads key data from the JSON file."""
    if not os.path.exists(KEYS_FILE):
        log_event(f"Keys file not found: {KEYS_FILE}. Returning empty data.", "info")
        return {}
    try:
        with open(KEYS_FILE, "r") as f:
            content = f.read()
            if not content.strip():
                log_event(f"Keys file is empty: {KEYS_FILE}. Returning empty data.", "info")
                return {}
            data = json.loads(content)
        return data
    except json.JSONDecodeError:
        log_event(f"Error decoding JSON from {KEYS_FILE}. Returning empty data.", "error")
        return {}
    except Exception as e:
        log_event(f"Unexpected error loading {KEYS_FILE}: {e}. Returning empty data.", "error")
        return {}

def _save_keys_data(data):
    """Saves key data to the JSON file."""
    try:
        dir_name = os.path.dirname(KEYS_FILE)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
        with open(KEYS_FILE, "w") as f:
            json.dump(data, f, indent=2)
        log_event(f"Successfully saved keys data to {KEYS_FILE}.", "info")
        return True
    except Exception as e:
        log_event(f"Error saving keys data to {KEYS_FILE}: {e}", "error")
        return False

# --- Key Management Functions ---
def set_key(service_name: str, key_name: str, key_value: str) -> bool:
    """
    Sets (adds or updates) a specific key for a given service.
    """
    if not service_name or not key_name:
        log_event("Service name and key name cannot be empty.", "error")
        return False

    keys_data = _load_keys_data()
    if service_name not in keys_data:
        keys_data[service_name] = {}
    keys_data[service_name][key_name] = key_value
    success = _save_keys_data(keys_data)
    if success:
        log_event(f"Key '{key_name}' set for service '{service_name}'.", "info")
    else:
        log_event(f"Failed to set key '{key_name}' for service '{service_name}'.", "error")
    return success

def get_key(service_name: str, key_name: str) -> str | None:
    """
    Retrieves a specific key for a given service.
    Returns the key value or None if not found.
    """
    keys_data = _load_keys_data()
    key_value = keys_data.get(service_name, {}).get(key_name)
    if key_value is not None:
        log_event(f"Key '{key_name}' retrieved for service '{service_name}'.", "debug") # Debug to avoid logging actual key values in normal ops
    else:
        log_event(f"Key '{key_name}' not found for service '{service_name}'.", "warning")
    return key_value

def delete_key(service_name: str, key_name: str) -> bool:
    """
    Deletes a specific key for a given service.
    Returns True if deletion was successful or key didn't exist, False on error.
    """
    keys_data = _load_keys_data()
    if service_name in keys_data and key_name in keys_data[service_name]:
        del keys_data[service_name][key_name]
        if not keys_data[service_name]: # If service has no keys left, remove service entry
            del keys_data[service_name]
        success = _save_keys_data(keys_data)
        if success:
            log_event(f"Key '{key_name}' deleted for service '{service_name}'.", "info")
        else:
            log_event(f"Failed to delete key '{key_name}' for service '{service_name}'.", "error")
        return success
    else:
        log_event(f"Key '{key_name}' not found for service '{service_name}', no deletion needed.", "info")
        return True # Considered success as the state matches desired outcome

def list_services() -> list[str]:
    """
    Lists all services that have keys stored.
    """
    keys_data = _load_keys_data()
    services = list(keys_data.keys())
    log_event(f"Retrieved list of services: {services}", "debug")
    return services

def list_keys(service_name: str) -> list[str] | None:
    """
    Lists all key names for a given service.
    Returns a list of key names or None if the service is not found.
    """
    keys_data = _load_keys_data()
    if service_name in keys_data:
        key_names = list(keys_data[service_name].keys())
        log_event(f"Retrieved list of keys for service '{service_name}': {key_names}", "debug")
        return key_names
    else:
        log_event(f"Service '{service_name}' not found for listing keys.", "warning")
        return None

# --- Future Security Enhancements ---
# TODO: Implement encryption for KEYS_FILE at rest.
# TODO: Consider using environment variables for sensitive keys where appropriate.
# TODO: Explore integration with dedicated secret management services (e.g., HashiCorp Vault, AWS Secrets Manager).
# IMPORTANT: This initial version stores keys in plain text in katana_keys.json.
# This file MUST be added to .gitignore and should NOT be committed to version control.
# For production systems, encryption or a proper secrets manager is crucial.

if __name__ == '__main__':
    # Basic test logic for the key manager
    log_event("katana_key_manager.py self-test started.", "info")

    # Ensure the keys file exists for testing (it would be created by katana_agent.py's init)
    if not os.path.exists(KEYS_FILE):
        _save_keys_data({})
        log_event(f"Self-test: Initialized empty {KEYS_FILE} for testing.", "info")
    else: # Clear the file for a clean test run if it exists
        _save_keys_data({})
        log_event(f"Self-test: Cleared existing {KEYS_FILE} for a clean test run.", "info")


    # Test set_key
    log_event("Self-test: Testing set_key...", "info")
    set_key("TestService1", "api_key", "test_value_123")
    set_key("TestService1", "secret_key", "another_secret")
    set_key("TestService2", "client_id", "client_abc")
    set_key("", "empty_service_key", "wont_be_set") # Test invalid input
    set_key("TestService3", "", "wont_be_set_either") # Test invalid input


    # Test get_key
    log_event("Self-test: Testing get_key...", "info")
    api_key = get_key("TestService1", "api_key")
    log_event(f"Self-test: Retrieved api_key for TestService1: {api_key}", "info")
    non_existent_key = get_key("TestService1", "non_existent")
    log_event(f"Self-test: Retrieving non_existent_key for TestService1: {non_existent_key}", "info")
    key_from_empty_service = get_key("", "some_key") # Test invalid input
    log_event(f"Self-test: Retrieving key_from_empty_service: {key_from_empty_service}", "info")

    # Test list_services
    log_event("Self-test: Testing list_services...", "info")
    services = list_services()
    log_event(f"Self-test: Available services: {services}", "info")

    # Test list_keys
    log_event("Self-test: Testing list_keys...", "info")
    service1_keys = list_keys("TestService1")
    log_event(f"Self-test: Keys for TestService1: {service1_keys}", "info")
    service_non_existent_keys = list_keys("NonExistentService")
    log_event(f"Self-test: Keys for NonExistentService: {service_non_existent_keys}", "info")

    # Test delete_key
    log_event("Self-test: Testing delete_key...", "info")
    delete_key("TestService1", "secret_key")
    service1_keys_after_delete = list_keys("TestService1")
    log_event(f"Self-test: Keys for TestService1 after deleting 'secret_key': {service1_keys_after_delete}", "info")
    delete_key("TestService2", "client_id") # This should remove TestService2 entry as well
    services_after_delete = list_services()
    log_event(f"Self-test: Available services after deleting TestService2's only key: {services_after_delete}", "info")
    delete_key("TestService1", "non_existent_key") # Test deleting non-existent key

    log_event("katana_key_manager.py self-test completed.", "info")
