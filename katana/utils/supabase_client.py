import os
import json
from katana.logger import get_logger

logger = get_logger(__name__)

class SupabaseMemoryClient:
    def __init__(self):
        """
        Initializes the SupabaseMemoryClient.
        Reads Supabase URL and Key from environment variables.
        """
        self.supabase_url = os.environ.get("SUPABASE_URL")
        self.supabase_key = os.environ.get("SUPABASE_KEY")
        self.client = None # Placeholder for actual Supabase client
        self.table_name = "command_traces"

        log_context = {'user_id': 'system_setup', 'chat_id': 'supabase_client_init'}

        if not self.supabase_url:
            logger.warning("SUPABASE_URL environment variable not set. SupabaseMemoryClient will not be functional.", extra=log_context)
        if not self.supabase_key:
            logger.warning("SUPABASE_KEY environment variable not set. SupabaseMemoryClient will not be functional.", extra=log_context)

        if self.supabase_url and self.supabase_key:
            try:
                # In a real scenario, you would initialize the Supabase client here.
                # from supabase import create_client, Client
                # self.client: Client = create_client(self.supabase_url, self.supabase_key)
                logger.info("SupabaseMemoryClient initialized (conceptually). Actual Supabase client setup would be here.", extra=log_context)
                # For this task, we'll simulate its presence.
                self.client = "mock_supabase_client_initialized"
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}", extra=log_context)
                self.client = None
        else:
            logger.info("SupabaseMemoryClient is not configured due to missing URL/key.", extra=log_context)

    def save_trace(self, trace_data: dict) -> bool:
        """
        Saves the trace data to a Supabase table.
        For now, it logs the trace data instead of sending it to Supabase.

        Args:
            trace_data (dict): The dictionary containing trace information.

        Returns:
            bool: True if the trace was "saved" (logged), False otherwise.
        """
        log_context = {
            'user_id': trace_data.get('user_id', 'system_trace'),
            'chat_id': trace_data.get('context_id', 'trace_saving'), # Assuming context_id might be used
            'message_id': trace_data.get('trace_id', 'unknown_trace')
        }

        if not self.client:
            logger.warning("Supabase client not initialized. Cannot save trace.", extra=log_context)
            return False

        try:
            # In a real scenario, you would insert data into Supabase:
            # data, error = self.client.table(self.table_name).insert(trace_data).execute()
            # if error and error[1]: # Check for actual error object in the tuple
            #     logger.error(f"Error saving trace to Supabase: {error[1]}", extra=log_context)
            #     return False
            # elif not data or not data[1]: # Check for actual data object in the tuple
            #     logger.warning(f"No data returned from Supabase insert or empty data: {data}", extra=log_context)
            #     # This might not be an error depending on Supabase client behavior
            #     return False # Or True, depending on strictness

            # For now, log the data that would be sent
            logger.info(
                f"Simulating save_trace to Supabase table '{self.table_name}'. Data: {json.dumps(trace_data)}",
                extra=log_context
            )
            return True
        except Exception as e:
            logger.error(f"An unexpected error occurred in save_trace: {e}", extra=log_context)
            return False

if __name__ == '__main__':
    # Example Usage (requires environment variables to be set for full functionality)
    # You would need to set SUPABASE_URL and SUPABASE_KEY in your environment
    # For example:
    # export SUPABASE_URL="your_supabase_url"
    # export SUPABASE_KEY="your_supabase_anon_key"

    from katana.logger import setup_logging
    import logging as py_logging # Alias to avoid confusion with local 'logger'
    setup_logging(log_level=py_logging.DEBUG)

    logger.info("--- Testing SupabaseMemoryClient ---")

    client = SupabaseMemoryClient()

    if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY"):
        logger.info("SUPABASE_URL and SUPABASE_KEY are set.")
    else:
        logger.warning("SUPABASE_URL and/or SUPABASE_KEY are NOT set. Client will operate in non-functional mode for actual Supabase connection.")

    test_trace = {
        "trace_id": "test-uuid-12345",
        "name": "test_function",
        "time_start": "2023-01-01T12:00:00Z",
        "time_end": "2023-01-01T12:00:01Z",
        "duration": 1.0,
        "args": [1, "arg2"],
        "kwargs": {"param1": True},
        "return_value": "success",
        "exception": None,
        "user_id": "test_user",
        "context_id": "test_session"
    }
    success = client.save_trace(test_trace)
    logger.info(f"save_trace call successful: {success}")

    # Test without client initialized (e.g., if keys were missing)
    # To simulate this properly, you might unset env vars or create a client instance
    # where initialization failed. For this example, we assume client might be None.
    if not client.client: # A bit of a hacky check for this test
        logger.info("Testing save_trace with uninitialized client (as if URL/Key were missing)...")
        uninitialized_client = SupabaseMemoryClient() # Create a new one to force re-check
        # Temporarily remove env vars for this specific test if they were set
        original_url = os.environ.pop("SUPABASE_URL", None)
        original_key = os.environ.pop("SUPABASE_KEY", None)

        clean_env_client = SupabaseMemoryClient()
        success_no_env = clean_env_client.save_trace(test_trace)
        logger.info(f"save_trace call with no env vars (simulated): {success_no_env}")

        # Restore env vars if they were originally set
        if original_url: os.environ["SUPABASE_URL"] = original_url
        if original_key: os.environ["SUPABASE_KEY"] = original_key
        logger.info("Environment variables restored if they were changed for the test.")

    logger.info("--- End of SupabaseMemoryClient Test ---")
