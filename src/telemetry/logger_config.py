import logging
from logging.handlers import RotatingFileHandler
import os

# Create logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Attempt to import Supabase handler and client
try:
    from .supabase_client import SupabaseTelemetryClient, SupabaseHandler
    # Initialize client once to see if it's viable
    # This will also load .env if SUPABASE_URL/KEY are not already in os.environ
    # by virtue of SupabaseTelemetryClient -> get_supabase_credentials -> load_dotenv
    # from supabase_config.py
    # However, it's better to ensure dotenv is loaded early if supabase_config.py relies on it.
    from dotenv import load_dotenv
    # Determine the correct path to .env. If logger_config.py is in src/telemetry,
    # .env is typically in the project root, two levels up.
    # This assumes standard project structure.
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
        # print(f"logger_config: Loaded .env from {dotenv_path}") # For debugging
    else:
        load_dotenv() # Try default location or existing env vars
        # print("logger_config: Attempted to load .env from default or used existing env vars")


    # Try to initialize the client to check if Supabase is configured
    # This client instance is just for the check; SupabaseHandler will create its own
    # or be passed one if we want to share a single client. For simplicity,
    # SupabaseHandler currently creates its own if not provided.
    temp_supabase_client = SupabaseTelemetryClient()
    if temp_supabase_client.get_client():
        supabase_handler_instance = SupabaseHandler(supabase_client=temp_supabase_client)
        # We could also set a specific format for Supabase if needed
        # supabase_handler_instance.setFormatter(logging.Formatter(...))
        supabase_enabled = True
        # print("logger_config: Supabase client initialized. SupabaseHandler will be active.") # For debugging
    else:
        supabase_enabled = False
        supabase_handler_instance = None
        # print("logger_config: Supabase client NOT initialized. SupabaseHandler will be inactive.") # For debugging
except ImportError:
    # print("logger_config: Supabase client/handler not found. Supabase logging disabled.") # For debugging
    supabase_enabled = False
    supabase_handler_instance = None
except ValueError as ve: # Raised by SupabaseTelemetryClient if creds are missing
    # print(f"logger_config: Supabase config error: {ve}. Supabase logging disabled.") # For debugging
    supabase_enabled = False
    supabase_handler_instance = None
except Exception as e:
    # print(f"logger_config: Unexpected error during Supabase setup: {e}. Supabase logging disabled.") # For debugging
    supabase_enabled = False
    supabase_handler_instance = None


# Configure logging
log_file = 'logs/app.log'

# Define handlers
handlers = [
    RotatingFileHandler(log_file, maxBytes=1024*1024*5, backupCount=5), # 5 MB per file, 5 backup files
    logging.StreamHandler() # Also log to console
]

if supabase_enabled and supabase_handler_instance:
    handlers.append(supabase_handler_instance)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)

# This initial basicConfig call might be overridden if other modules call it.
# A more robust way for libraries is to get the root logger and add handlers.
# For an application's main config, basicConfig is often okay if called early.

# Alternatively, to avoid basicConfig re-configuration issues:
# root_logger = logging.getLogger()
# root_logger.setLevel(logging.INFO)
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# for handler in handlers:
#     handler.setFormatter(formatter) # Ensure all handlers use the same format if desired
#     root_logger.addHandler(handler)


def get_logger(name):
    # After basicConfig, getLogger should return loggers configured with these handlers.
    return logging.getLogger(name)
