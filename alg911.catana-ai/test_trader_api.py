import pytest
import requests # To make HTTP requests to the API
import json
import os
import time
import subprocess # To run the API server as a separate process
from urllib.parse import urljoin

# Assuming shared_config.py is in the same directory or Python path
try:
    import shared_config
    COMMANDS_FILE = shared_config.COMMANDS_FILE_PATH
    TRADER_API_PORT = shared_config.TRADER_API_PORT
    TRADER_API_HOST = shared_config.TRADER_API_HOST
except ImportError:
    # Fallback if running test where shared_config isn't directly importable
    # This might happen depending on how pytest discovers/runs tests.
    # For robustness, ensure PYTHONPATH is set up if running from root or use relative imports.
    print("Warning: Could not import shared_config. Using default paths/ports for tests.")
    # Determine script directory to find sibling files if shared_config fails
    TEST_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    COMMANDS_FILE = os.path.join(TEST_SCRIPT_DIR, "katana.commands.json")
    TRADER_API_PORT = 5001 # Default from trader_api.py if shared_config fails
    TRADER_API_HOST = "127.0.0.1" # Localhost for testing


BASE_URL = f"http://{TRADER_API_HOST}:{TRADER_API_PORT}/"
TRADER_API_SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trader_api.py")

@pytest.fixture(scope="module")
def trader_api_server():
    """Fixture to start and stop the Trader API server for the test module."""
    # Ensure commands file is clean before starting
    if os.path.exists(COMMANDS_FILE):
        with open(COMMANDS_FILE, "w") as f:
            json.dump([], f) # Initialize with an empty list

    # Start the Flask server as a subprocess
    # Use "python" or "python3" depending on your environment
    python_executable = "python3" # Or just "python"
    try:
        # Check if python3 is available, otherwise use python
        subprocess.check_call([python_executable, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except (subprocess.CalledProcessError, FileNotFoundError):
        python_executable = "python"

    server_process = subprocess.Popen([python_executable, TRADER_API_SCRIPT_PATH])

    # Wait for the server to start - adjust time as needed
    time.sleep(2) # Give it a couple of seconds to boot up

    # Verify server is up
    retries = 5
    server_ready = False
    for i in range(retries):
        try:
            response = requests.get(urljoin(BASE_URL, "trader/status"), timeout=1)
            if response.status_code == 200:
                server_ready = True
                break
        except requests.ConnectionError:
            time.sleep(1) # Wait and retry

    if not server_ready:
        server_process.terminate() # Try to kill it if it didn't start
        server_process.wait()
        pytest.fail("Trader API server did not start within the allotted time.")

    yield # This is where the tests will run

    # Teardown: Stop the server
    server_process.terminate()
    server_process.wait()

    # Clean up commands file after tests
    if os.path.exists(COMMANDS_FILE):
        with open(COMMANDS_FILE, "w") as f:
            json.dump([], f)

def test_api_connection(trader_api_server):
    """Test that the API server is running and reachable."""
    # The fixture already checks this, but an explicit test is good.
    try:
        response = requests.get(urljoin(BASE_URL, "trader/status"))
        assert response.status_code == 200
        assert response.json().get("status") == "ok"
    except requests.ConnectionError:
        pytest.fail("Failed to connect to the Trader API server. Is it running?")

def test_trader_status_endpoint(trader_api_server):
    """Test the /trader/status endpoint."""
    response = requests.get(urljoin(BASE_URL, "trader/status"))
    assert response.status_code == 200
    json_response = response.json()
    assert json_response["status"] == "ok"
    assert "message" in json_response
    assert "timestamp" in json_response

def test_post_trader_command_valid(trader_api_server):
    """Test posting a valid command to /trader/command."""
    # Ensure a clean state for COMMANDS_FILE for this specific test if needed,
    # though fixture should handle module-level.
    # For this test, we'll append.
    initial_commands_count = 0
    if os.path.exists(COMMANDS_FILE):
        with open(COMMANDS_FILE, "r") as f:
            try:
                initial_commands_count = len(json.load(f))
            except json.JSONDecodeError:
                # File might be empty or malformed, treat as 0
                initial_commands_count = 0


    payload = {
        "command_type": "TEST_BUY",
        "symbol": "XYZ",
        "quantity": 10,
        "source": "pytest_trader_api"
    }
    response = requests.post(urljoin(BASE_URL, "trader/command"), json=payload)

    assert response.status_code == 201 # Created
    json_response = response.json()
    assert json_response["status"] == "success"
    assert "command_id" in json_response
    command_id = json_response["command_id"]

    # Verify the command was written to commands.json
    assert os.path.exists(COMMANDS_FILE), f"{COMMANDS_FILE} was not created."

    with open(COMMANDS_FILE, "r") as f:
        try:
            commands_in_file = json.load(f)
        except json.JSONDecodeError:
            pytest.fail(f"Could not decode JSON from {COMMANDS_FILE}. Content: {f.read()}")

    assert len(commands_in_file) == initial_commands_count + 1

    found_command = None
    for cmd in commands_in_file:
        if cmd.get("command_id") == command_id:
            found_command = cmd
            break

    assert found_command is not None, f"Command with ID {command_id} not found in {COMMANDS_FILE}"
    assert found_command["command_details"]["command_type"] == "TEST_BUY"
    assert found_command["command_details"]["symbol"] == "XYZ"
    assert found_command["command_details"]["quantity"] == 10
    assert found_command["source"] == "pytest_trader_api" # Checking if source from payload is used
    assert found_command["status"] == "pending"

def test_post_trader_command_invalid_no_json(trader_api_server):
    """Test posting a non-JSON payload to /trader/command."""
    response = requests.post(urljoin(BASE_URL, "trader/command"), data="not json")
    assert response.status_code == 400 # Bad Request
    json_response = response.json()
    assert json_response["status"] == "error"
    assert "Request must be JSON" in json_response["message"]

def test_post_trader_command_missing_type(trader_api_server):
    """Test posting a JSON payload missing 'command_type'."""
    payload = {
        "symbol": "ABC",
        "quantity": 5
    }
    response = requests.post(urljoin(BASE_URL, "trader/command"), json=payload)
    assert response.status_code == 400 # Bad Request
    json_response = response.json()
    assert json_response["status"] == "error"
    assert "Missing 'command_type'" in json_response["message"]

# Example of how one might run this:
# Ensure Flask and requests are installed: pip install Flask requests pytest
# Then run from the alg911.catana-ai directory: pytest test_trader_api.py
# Make sure trader_api.py and shared_config.py are in the same directory or accessible via PYTHONPATH
if __name__ == '__main__':
    # This allows running the test file directly for debugging / manual execution
    # Note: pytest fixtures might behave differently or not at all if not run via pytest CLI
    print("Running tests (manual execution mode - use `pytest` for full features)...")

    # Manual setup (simplified version of fixture)
    print("Setting up for manual test run...")
    if os.path.exists(COMMANDS_FILE):
        with open(COMMANDS_FILE, "w") as f: json.dump([], f)

    python_exec = "python3"
    try: subprocess.check_call([python_exec, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except: python_exec = "python"

    print(f"Starting server with: {python_exec} {TRADER_API_SCRIPT_PATH}")
    server_proc = subprocess.Popen([python_exec, TRADER_API_SCRIPT_PATH])
    time.sleep(3) # Wait for server

    try:
        print("Testing API connection...")
        response = requests.get(urljoin(BASE_URL, "trader/status"))
        print(f"Status response: {response.status_code}, {response.text}")
        assert response.status_code == 200

        print("\nTesting command post...")
        payload = {"command_type": "MANUAL_TEST", "symbol": "MAN", "quantity": 1}
        response = requests.post(urljoin(BASE_URL, "trader/command"), json=payload)
        print(f"Command post response: {response.status_code}, {response.text}")
        assert response.status_code == 201
        if os.path.exists(COMMANDS_FILE):
            with open(COMMANDS_FILE, "r") as f:
                print(f"\nContents of {COMMANDS_FILE}:")
                print(f.read())
        else:
            print(f"\n{COMMANDS_FILE} not found.")

    except Exception as e:
        print(f"An error occurred during manual test: {e}")
    finally:
        print("\nShutting down server...")
        server_proc.terminate()
        server_proc.wait()
        if os.path.exists(COMMANDS_FILE): # Clean up
             with open(COMMANDS_FILE, "w") as f: json.dump([], f)
        print("Manual test run finished.")
