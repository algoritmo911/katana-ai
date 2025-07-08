from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
from .supabase_config import get_supabase_credentials
# It's good practice to get a logger for this module as well.
# Assuming logger_config is in the same directory or accessible.
# from .logger_config import get_logger # Or adjust path as needed
import logging # Using standard logging for now if get_logger is complex to init here

# logger = get_logger(__name__) # If using your custom logger
logger = logging.getLogger(__name__) # Using standard logger

_supabase_client: Client | None = None
_supabase_url: str | None = None
_supabase_key: str | None = None

class SupabaseTelemetryClient:
    """
    A client to interact with Supabase for telemetry purposes.
    Initializes the Supabase client using credentials from environment variables.
    Provides methods to send data to specified tables.
    """
    def __init__(self, url: str | None = None, key: str | None = None, client_options: ClientOptions | None = None):
        """
        Initializes the Supabase client.
        If url and key are not provided, it attempts to load them using get_supabase_credentials.

        Args:
            url (str, optional): Supabase project URL.
            key (str, optional): Supabase service key or anon key.
            client_options (ClientOptions, optional): Options for the Supabase client.

        Raises:
            ValueError: If Supabase URL or Key cannot be determined.
        """
        global _supabase_client, _supabase_url, _supabase_key

        if url and key:
            self._url = url
            self._key = key
        else:
            try:
                self._url, self._key = get_supabase_credentials()
            except ValueError as e:
                logger.error(f"Failed to get Supabase credentials: {e}")
                # Depending on strictness, could raise here or allow client to be None
                # For telemetry, it might be acceptable to fail silently if not configured
                self._client = None
                _supabase_client = None
                raise # Re-raise for now, as telemetry is the goal

        if self._url and self._key:
            # Use provided client_options or default if None
            options = client_options if client_options else ClientOptions()
            try:
                self._client = create_client(self._url, self._key, options)
                _supabase_client = self._client # Cache client globally if needed by other parts
                _supabase_url = self._url
                _supabase_key = self._key
                logger.info("Supabase client initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to create Supabase client: {e}", exc_info=True)
                self._client = None
                _supabase_client = None
        else:
            self._client = None
            logger.warning("Supabase client not initialized due to missing URL or key.")

    def get_client(self) -> Client | None:
        """Returns the initialized Supabase client instance."""
        return self._client

    def send_data(self, table_name: str, data: dict) -> tuple[bool, any]:
        """
        Sends data to the specified Supabase table.

        Args:
            table_name (str): The name of the table to insert data into.
            data (dict): The data to insert, as a dictionary.

        Returns:
            tuple[bool, any]: A tuple containing a boolean success status
                              and the API response or error message.
        """
        if not self._client:
            logger.warning(f"Supabase client not initialized. Cannot send data to table '{table_name}'.")
            return False, "Client not initialized"

        try:
            response = self._client.table(table_name).insert(data).execute()
            # Add more robust error checking based on response structure
            if hasattr(response, 'error') and response.error:
                logger.error(f"Error sending data to Supabase table '{table_name}': {response.error.message}")
                return False, response.error
            # Sometimes errors might be in response.data as a list of errors for bulk, or other formats
            # For a single insert, data should be a list with one item typically
            if hasattr(response, 'data') and response.data:
                 logger.info(f"Data successfully sent to Supabase table '{table_name}'. Response: {response.data}")
                 return True, response.data
            else: # Handle cases where response structure is unexpected
                logger.warning(f"Unexpected response structure from Supabase for table '{table_name}': {response}")
                # Check if there's a status code to infer success/failure
                status_code = getattr(response, 'status_code', None)
                if status_code and 200 <= status_code < 300:
                    logger.info(f"Data sent to Supabase table '{table_name}', but response data is empty/unexpected. Status: {status_code}")
                    return True, response # Assuming success if status is 2xx
                else:
                    logger.error(f"Failed to send data to Supabase table '{table_name}'. Status: {status_code}, Response: {response}")
                    return False, response

        except Exception as e:
            logger.error(f"Exception sending data to Supabase table '{table_name}': {e}", exc_info=True)
            return False, str(e)

# Global instance for convenience, initialized on first import or explicitly
# This allows other modules to import and use a pre-configured client.
# However, direct instantiation `SupabaseTelemetryClient()` is often cleaner.
# For now, let's not auto-initialize a global one to give more control.

# Example usage (primarily for testing this module directly):
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO) # Basic logging for testing

    # This will require SUPABASE_URL and SUPABASE_KEY to be in environment
    # Create a .env file in the root with:
    # SUPABASE_URL="your_url"
    # SUPABASE_KEY="your_key"

    logger.info("Attempting to initialize SupabaseTelemetryClient...")
    try:
        # Ensure .env is in the project root or vars are exported for this to work
        from dotenv import load_dotenv
        # Assuming .env is in project root, one level up from src/telemetry
        dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path=dotenv_path)
            logger.info(f"Loaded .env file from: {dotenv_path}")
        else:
            # Fallback for cases where .env might be located elsewhere or vars are directly in env
            load_dotenv()
            logger.info("Attempted to load .env from default location or using existing env vars.")

        supabase_telemetry_client = SupabaseTelemetryClient()

        if supabase_telemetry_client.get_client():
            logger.info("SupabaseTelemetryClient initialized successfully.")

            # Example: Send a test event
            # IMPORTANT: Replace "test_events" with an actual table name in your Supabase.
            # You'll need to create this table in your Supabase project dashboard.
            # Example table columns: id (auto-gen), created_at (auto-gen), event_name (text), payload (jsonb)
            test_table = "analytics_events" # MAKE SURE THIS TABLE EXISTS
            test_data = {"event_name": "test_event_from_client", "payload": {"value": 123, "source": "katana-ai"}}

            logger.info(f"Sending test data to table: {test_table}")
            success, response = supabase_telemetry_client.send_data(test_table, test_data)

            if success:
                logger.info(f"Test data sent successfully. Response: {response}")
            else:
                logger.error(f"Failed to send test data. Error/Response: {response}")
        else:
            logger.error("SupabaseTelemetryClient could not be initialized. Check credentials and config.")

    except ValueError as ve:
        logger.error(f"Configuration error: {ve}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during __main__ execution: {e}", exc_info=True)

    # Note: For actual table creation (e.g., 'analytics_events'), this would typically be done
    # via Supabase Studio (SQL editor) or a migration script, not directly in the client code.
    # Example SQL for 'analytics_events' table:
    # CREATE TABLE public.analytics_events (
    #     id bigint NOT NULL GENERATED BY DEFAULT AS IDENTITY,
    #     created_at timestamp with time zone NOT NULL DEFAULT now(),
    #     event_name text NULL,
    #     payload jsonb NULL,
    #     CONSTRAINT analytics_events_pkey PRIMARY KEY (id)
    # );
    # Make sure RLS policies are set up if you are not using the service_role key.
    # If using service_role key, RLS is bypassed.
    # For anon key, you might need policies like:
    # CREATE POLICY "Enable insert for anon users" ON public.analytics_events FOR INSERT TO anon WITH CHECK (true);
    # CREATE POLICY "Enable read for anon users" ON public.analytics_events FOR SELECT TO anon USING (true);

import logging # For SupabaseHandler

class SupabaseHandler(logging.Handler):
    """
    A logging handler that sends log records to a Supabase table.
    """
    def __init__(self, supabase_client: SupabaseTelemetryClient | None = None, table_name: str = "log_entries"):
        """
        Initializes the handler.

        Args:
            supabase_client (SupabaseTelemetryClient, optional): An instance of SupabaseTelemetryClient.
                               If None, a new one will be attempted to be created.
            table_name (str): The name of the Supabase table to send log entries to.
        """
        super().__init__()
        if supabase_client:
            self.supabase_client = supabase_client
        else:
            try:
                self.supabase_client = SupabaseTelemetryClient()
            except ValueError: # Raised if URL/Key are missing
                self.supabase_client = None # Will not log to Supabase
                logger.warning("SupabaseHandler: SupabaseTelemetryClient could not be initialized. Logs will not be sent to Supabase.")
            except Exception as e:
                self.supabase_client = None
                logger.error(f"SupabaseHandler: Error initializing SupabaseTelemetryClient: {e}", exc_info=True)

        self.table_name = table_name

    def emit(self, record: logging.LogRecord):
        """
        Formats and sends the log record to Supabase.

        Args:
            record (logging.LogRecord): The log record to process.
        """
        if not self.supabase_client or not self.supabase_client.get_client():
            # Silently ignore if client is not available, or log to a fallback mechanism if desired
            return

import datetime # For timestamp formatting

class SupabaseHandler(logging.Handler):
    """
    A logging handler that sends log records to a Supabase table.
    """
    def __init__(self, supabase_client: SupabaseTelemetryClient | None = None, table_name: str = "log_entries"):
        """
        Initializes the handler.

        Args:
            supabase_client (SupabaseTelemetryClient, optional): An instance of SupabaseTelemetryClient.
                               If None, a new one will be attempted to be created.
            table_name (str): The name of the Supabase table to send log entries to.
        """
        super().__init__()
        # Ensure there's a default formatter if none is set by the time emit is called
        if self.formatter is None:
            self.formatter = logging.Formatter()

        if supabase_client:
            self.supabase_client = supabase_client
        else:
            try:
                self.supabase_client = SupabaseTelemetryClient()
            except ValueError: # Raised if URL/Key are missing
                self.supabase_client = None # Will not log to Supabase
                logger.warning("SupabaseHandler: SupabaseTelemetryClient could not be initialized. Logs will not be sent to Supabase.")
            except Exception as e:
                self.supabase_client = None
                logger.error(f"SupabaseHandler: Error initializing SupabaseTelemetryClient: {e}", exc_info=True)

        self.table_name = table_name

    def emit(self, record: logging.LogRecord):
        """
        Formats and sends the log record to Supabase.

        Args:
            record (logging.LogRecord): The log record to process.
        """
        if not self.supabase_client or not self.supabase_client.get_client():
            # Silently ignore if client is not available, or log to a fallback mechanism if desired
            return

        try:
            # Ensure asctime is available on the record, usually done by formatter.format()
            # but we might be calling getMessage() before self.format()
            if not hasattr(record, 'asctime'):
                if self.formatter:
                    record.asctime = self.formatter.formatTime(record, self.formatter.datefmt)
                else: # Fallback basic asctime
                    record.asctime = datetime.datetime.fromtimestamp(record.created).isoformat()


            log_entry = {
                # Use ISO format for timestamp for better database compatibility
                "timestamp": datetime.datetime.fromtimestamp(record.created).isoformat(),
                "level_name": record.levelname,
                "level_number": record.levelno,
                "logger_name": record.name,
                "module": record.module,
                "filename": record.filename,
                "line_number": record.lineno,
                "function_name": record.funcName,
                "message": self.format(record), # Formatted log message
                "raw_message": record.getMessage(), # Unformatted message
                "exception_info": self.formatException(record.exc_info) if record.exc_info else None,
                "process_id": record.process,
                "thread_id": record.thread,
                "thread_name": record.threadName,
            }
            # Remove None values to keep payload clean, if desired
            # log_entry = {k: v for k, v in log_entry.items() if v is not None}

            success, response = self.supabase_client.send_data(self.table_name, log_entry)
            if not success:
                # Be careful about logging errors from a logger handler to avoid loops
                # print(f"SupabaseHandler: Failed to send log to Supabase. Response: {response}") # Use print for handler errors
                pass # Or log to a different, failsafe logger
        except Exception as e:
            # print(f"SupabaseHandler: Exception during emit. {e}") # Use print for handler errors
            self.handleError(record) # Default handler error handling


# To define table structures:
# This client does not handle table creation. Tables should be defined in Supabase.
# Example table for trades:
# Table: trades
# Columns:
#   id (primary key, auto-increment)
#   timestamp (timestamp with time zone, default now())
#   symbol (text)
#   type (text, e.g., 'buy', 'sell')
#   price (numeric)
#   quantity (numeric)
#   metadata (jsonb, optional for extra details)

# Example table for system events:
# Table: system_events
# Columns:
#   id (primary key, auto-increment)
#   timestamp (timestamp with time zone, default now())
#   event_type (text, e.g., 'startup', 'shutdown', 'error')
#   message (text)
#   details (jsonb, optional for stack traces or other info)
