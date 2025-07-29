import json
from pathlib import Path

def get_auth_token():
    """
    Gets the auth token from ~/.katana/cli_auth.json.
    """
    auth_file = Path.home() / ".katana" / "cli_auth.json"
    if not auth_file.exists():
        return None

    with open(auth_file, "r") as f:
        try:
            data = json.load(f)
            return data.get("token")
        except json.JSONDecodeError:
            return None
