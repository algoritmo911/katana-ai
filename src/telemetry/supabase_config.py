import os
from dotenv import load_dotenv

# Load environment variables from .env file, if it exists
load_dotenv()

# Load environment variables from secrets.toml if .env is not used or specific keys are missing
# This part assumes that secrets.toml is parsed and loaded into env vars elsewhere
# or that you adapt this to read directly from secrets.toml using toml library.
# For simplicity, we'll rely on os.environ which can be populated by various means.

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def get_supabase_credentials():
    """
    Retrieves Supabase URL and Key from environment variables.

    Returns:
        tuple: (SUPABASE_URL, SUPABASE_KEY)

    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_KEY is not set.
    """
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url:
        raise ValueError("SUPABASE_URL environment variable not set.")
    if not key:
        raise ValueError("SUPABASE_KEY environment variable not set.")

    return url, key

if __name__ == "__main__":
    # Example of how to use it and test if variables are loaded
    try:
        url, key = get_supabase_credentials()
        print(f"Supabase URL: {url}")
        print(f"Supabase Key: {'*' * len(key) if key else None}") # Avoid printing the key
        print("Supabase configuration seems OK.")
    except ValueError as e:
        print(f"Error: {e}")
        print("Please ensure SUPABASE_URL and SUPABASE_KEY are set in your environment or .env file.")

# It's also good practice to add to secrets.toml.example
# SUPABASE_URL = "your_supabase_url"
# SUPABASE_KEY = "your_supabase_key"
