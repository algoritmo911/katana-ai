import json
import os
from datetime import datetime, timezone
from .supabase_client import get_supabase_client

# Define the directory and filenames for storing fetched data
DATA_DIR = "data/supabase_sync"
KNOWLEDGE_FILE = os.path.join(DATA_DIR, "knowledge.json")
REFLECTIONS_FILE = os.path.join(DATA_DIR, "reflections.json")
SYNC_LOG_FILE = os.path.join(DATA_DIR, "sync_log.json")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

def _load_json_data(filepath: str) -> list:
    """Helper to load data from a JSON file."""
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return [] # Return empty list if file is corrupt or empty
    return []

def _save_json_data(filepath: str, data: list):
    """Helper to save data to a JSON file."""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

def _log_sync_activity(table_name: str, success: bool, count: int = 0, error_message: str = None):
    """Logs synchronization activity."""
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "table_name": table_name,
        "success": success,
        "records_synced": count,
        "error": error_message if error_message else "None"
    }

    sync_logs = _load_json_data(SYNC_LOG_FILE)
    sync_logs.append(log_entry)
    _save_json_data(SYNC_LOG_FILE, sync_logs)

def fetch_new_knowledge_from_supabase(table_name: str = "knowledge") -> tuple[bool, int]:
    """
    Fetches new records from the specified 'knowledge' table in Supabase.
    It assumes records have an 'id' and potentially 'created_at' or 'updated_at'
    field to help determine newness, though a simpler full fetch is implemented here.
    For a more robust solution, delta fetching (only new/updated records) is recommended.

    Args:
        table_name (str): The name of the Supabase table to fetch from.

    Returns:
        tuple[bool, int]: A tuple containing:
            - bool: True if sync was successful, False otherwise.
            - int: Number of records fetched.
    """
    supabase = get_supabase_client()
    if not supabase:
        print("Supabase client not available. Cannot fetch knowledge.")
        _log_sync_activity(table_name, success=False, error_message="Supabase client not initialized.")
        return False, 0

    try:
        # Fetch all records from the table for simplicity.
        # For large datasets, implement pagination and delta fetching (e.g., based on a timestamp).
        response = supabase.table(table_name).select("*").execute()

        if response.data:
            _save_json_data(KNOWLEDGE_FILE, response.data)
            count = len(response.data)
            print(f"Successfully fetched {count} records from '{table_name}' and saved to {KNOWLEDGE_FILE}.")
            _log_sync_activity(table_name, success=True, count=count)
            return True, count
        else:
            # Handle cases where response.data might be None or empty without an explicit error
            # This could occur if the table is empty or if there's an issue not raising an exception.
            if hasattr(response, 'error') and response.error:
                 error_msg = str(response.error.message if hasattr(response.error, 'message') else response.error)
                 print(f"Error fetching data from '{table_name}': {error_msg}")
                 _log_sync_activity(table_name, success=False, error_message=error_msg)
                 return False, 0

            # If no data and no explicit error, assume table is empty or no new data based on query
            print(f"No data returned from '{table_name}'. Assuming table is empty or no new data based on query.")
            _save_json_data(KNOWLEDGE_FILE, []) # Save empty list to indicate a successful sync of zero records
            _log_sync_activity(table_name, success=True, count=0) # Log as success with 0 records
            return True, 0

    except Exception as e:
        error_msg = f"An unexpected error occurred while fetching from '{table_name}': {e}"
        print(error_msg)
        _log_sync_activity(table_name, success=False, error_message=str(e))
        return False, 0

def fetch_new_reflections_from_supabase(table_name: str = "reflections") -> tuple[bool, int]:
    """
    Fetches new records from the specified 'reflections' table in Supabase.
    Similar to fetch_new_knowledge_from_supabase, this is a simple full fetch.

    Args:
        table_name (str): The name of the Supabase table to fetch from.

    Returns:
        tuple[bool, int]: A tuple containing:
            - bool: True if sync was successful, False otherwise.
            - int: Number of records fetched.
    """
    supabase = get_supabase_client()
    if not supabase:
        print("Supabase client not available. Cannot fetch reflections.")
        _log_sync_activity(table_name, success=False, error_message="Supabase client not initialized.")
        return False, 0

    try:
        response = supabase.table(table_name).select("*").execute()

        if response.data:
            _save_json_data(REFLECTIONS_FILE, response.data)
            count = len(response.data)
            print(f"Successfully fetched {count} records from '{table_name}' and saved to {REFLECTIONS_FILE}.")
            _log_sync_activity(table_name, success=True, count=count)
            return True, count
        else:
            if hasattr(response, 'error') and response.error:
                 error_msg = str(response.error.message if hasattr(response.error, 'message') else response.error)
                 print(f"Error fetching data from '{table_name}': {error_msg}")
                 _log_sync_activity(table_name, success=False, error_message=error_msg)
                 return False, 0

            print(f"No data returned from '{table_name}'. Assuming table is empty or no new data based on query.")
            _save_json_data(REFLECTIONS_FILE, [])
            _log_sync_activity(table_name, success=True, count=0)
            return True, 0

    except Exception as e:
        error_msg = f"An unexpected error occurred while fetching from '{table_name}': {e}"
        print(error_msg)
        _log_sync_activity(table_name, success=False, error_message=str(e))
        return False, 0

def synchronize_all_data():
    """
    Synchronizes all relevant data (knowledge, reflections) from Supabase.
    """
    print("Starting data synchronization with Supabase...")

    knowledge_success, knowledge_count = fetch_new_knowledge_from_supabase()
    reflections_success, reflections_count = fetch_new_reflections_from_supabase()

    if knowledge_success and reflections_success:
        print(f"Data synchronization complete. Fetched {knowledge_count} knowledge entries and {reflections_count} reflection entries.")
    else:
        print("Data synchronization encountered errors. Check logs for details.")

if __name__ == "__main__":
    # This is for testing purposes.
    # Ensure Supabase client is configured via secrets.toml or environment variables.
    print("Running knowledge base synchronization test...")

    # To test this, you would need Supabase instance with 'knowledge' and 'reflections' tables.
    # Example:
    # client = get_supabase_client()
    # if client:
    #     # Create dummy tables if they don't exist (for testing only, requires admin rights)
    #     # This is complex to do safely here. Assume tables exist for the test.
    #     print("Attempting to sync all data...")
    #     synchronize_all_data()
    # else:
    #     print("Supabase client not configured. Skipping test.")

    # For now, just call synchronize_all_data and it will print messages
    # based on whether the client is configured and if tables exist.
    synchronize_all_data()

    print("\nContents of sync log:")
    if os.path.exists(SYNC_LOG_FILE):
        with open(SYNC_LOG_FILE, 'r') as f:
            print(f.read())
    else:
        print("Sync log is empty or not created yet.")

    print("\nKnowledge file location:", os.path.abspath(KNOWLEDGE_FILE))
    print("Reflections file location:", os.path.abspath(REFLECTIONS_FILE))

    # Note: Actual data fetching depends on live Supabase tables named 'knowledge' and 'reflections'.
    # If these tables don't exist or are not accessible, the sync functions will log errors.
