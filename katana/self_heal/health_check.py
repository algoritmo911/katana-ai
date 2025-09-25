import os
import time
import openai
import urllib.request

# --- Configuration ---
# In a real app, these would be managed more robustly (e.g., via a config object)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
N8N_URL = os.getenv("N8N_URL")
N8N_API_KEY = os.getenv("N8N_API_KEY")

MAX_RETRIES = 3
INITIAL_DELAY_SECONDS = 1

# --- Service Check Functions ---

def _check_service_with_retry(check_function, service_name):
    """
    Generic retry logic for a service check function.

    Args:
        check_function (callable): The function that performs the actual check.
        service_name (str): The name of the service for logging.

    Returns:
        bool: True if the service is healthy, False otherwise.
    """
    delay = INITIAL_DELAY_SECONDS
    for attempt in range(MAX_RETRIES):
        if check_function():
            print(f"✅ {service_name} is operational.")
            return True
        else:
            if attempt < MAX_RETRIES - 1:
                print(f"⚠️ {service_name} check failed. Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                print(f"🚨 CRITICAL: {service_name} is unreachable after {MAX_RETRIES} attempts.")
                # In a real system, this would trigger a formal alert.
                # For now, we print to console as per requirements.
    return False

def check_openai():
    """Checks the status of the OpenAI API."""
    def _check():
        if not OPENAI_API_KEY:
            print("ERROR: OPENAI_API_KEY environment variable not set.")
            return False
        try:
            openai.api_key = OPENAI_API_KEY
            # A lightweight, non-resource-intensive API call to verify connectivity and auth.
            openai.Model.list()
            return True
        except Exception as e:
            print(f"OpenAI API check failed with error: {e}")
            return False
    return _check_service_with_retry(_check, "OpenAI API")

def check_supabase():
    """
    Checks the status of Supabase.
    This is a placeholder, as a real check depends on the Supabase service (e.g., REST, Auth).
    Here, we simulate checking a hypothetical health endpoint.
    """
    def _check():
        if not SUPABASE_URL or not SUPABASE_KEY:
            print("ERROR: SUPABASE_URL or SUPABASE_KEY environment variables not set.")
            return False
        try:
            # A real check would target a specific health or status endpoint.
            # e.g., f"{SUPABASE_URL}/rest/v1/"
            req = urllib.request.Request(SUPABASE_URL, headers={"apikey": SUPABASE_KEY})
            with urllib.request.urlopen(req, timeout=10) as response:
                # We expect a 2xx status code for a healthy service.
                return 200 <= response.status < 300
        except Exception as e:
            print(f"Supabase check failed with error: {e}")
            return False
    return _check_service_with_retry(_check, "Supabase")

def check_n8n():
    """
    Checks the status of the n8n workflow automation service.
    This is a placeholder, simulating a check to a health endpoint.
    """
    def _check():
        if not N8N_URL or not N8N_API_KEY:
            print("ERROR: N8N_URL or N8N_API_KEY environment variables not set.")
            return False
        try:
            # n8n has a health check endpoint: /healthz
            health_url = f"{N8N_URL.rstrip('/')}/healthz"
            req = urllib.request.Request(health_url, headers={"X-N8N-API-KEY": N8N_API_KEY})
            with urllib.request.urlopen(req, timeout=10) as response:
                return 200 <= response.status < 300
        except Exception as e:
            print(f"n8n check failed with error: {e}")
            return False
    return _check_service_with_retry(_check, "n8n")


# --- Main Orchestrator ---

def run_health_check():
    """
    Runs a comprehensive health check of all critical external services.
    """
    print("\n--- Starting System Health Check ---")

    # The services to check are defined here
    services_to_check = {
        "OpenAI": check_openai,
        "Supabase": check_supabase,
        "n8n": check_n8n,
    }

    all_systems_go = True
    for service_name, check_func in services_to_check.items():
        if not check_func():
            all_systems_go = False
            print(f"💔 Health check failed for: {service_name}")

    print("\n--- Health Check Complete ---")
    if all_systems_go:
        print("✅ All systems are nominal.")
    else:
        print("🚨 One or more systems are experiencing issues. Please review logs.")
        # This is where an escalation policy would be triggered.

if __name__ == "__main__":
    # This allows the script to be run directly for manual checks.
    # For a real deployment, you would import and call run_health_check()
    # from a management script or a CLI command.
    run_health_check()
