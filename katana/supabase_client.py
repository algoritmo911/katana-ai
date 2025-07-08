import os
import toml
from supabase import create_client, Client

# Path to the secrets.toml file
SECRETS_FILE = "secrets.toml"

def load_supabase_config():
    """Loads Supabase URL and Key from secrets.toml."""
    try:
        with open(SECRETS_FILE, 'r') as f:
            secrets = toml.load(f)

        supabase_url = secrets.get("supabase", {}).get("url")
        supabase_key = secrets.get("supabase", {}).get("key")

        if not supabase_url or not supabase_key:
            raise ValueError("Supabase URL or Key is missing in secrets.toml")

        return supabase_url, supabase_key
    except FileNotFoundError:
        # Fallback to environment variables if secrets.toml is not found
        # This is useful for deployment environments like GitHub Actions
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not found in secrets.toml or environment variables.")

        return supabase_url, supabase_key
    except Exception as e:
        print(f"Error loading Supabase configuration: {e}")
        raise

# Initialize Supabase client
try:
    SUPABASE_URL, SUPABASE_KEY = load_supabase_config()
    supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Successfully connected to Supabase.")
except ValueError as e:
    print(f"Failed to initialize Supabase client: {e}")
    # You might want to handle this more gracefully depending on your application's needs
    # For example, disable features that require Supabase or exit if it's critical.
    supabase_client = None

def get_supabase_client() -> Client | None:
    """Returns the initialized Supabase client."""
    return supabase_client

if __name__ == "__main__":
    # This is for testing purposes.
    # To run this, make sure you have a valid secrets.toml or environment variables.
    client = get_supabase_client()
    if client:
        print("Supabase client is available.")
        # Example: List tables (requires appropriate permissions)
        # try:
        #     # Note: Supabase Python client doesn't have a direct "list tables" method
        #     # like some other database clients. You typically interact with specific tables.
        #     # This is a placeholder for a simple interaction.
        #     # For example, trying to select from a known table:
        #     response = client.table('your_table_name').select("*").limit(1).execute()
        #     print("Test query response:", response)
        # except Exception as e:
        #     print(f"Error during test query: {e}")
    else:
        print("Supabase client is not available. Check configuration.")
