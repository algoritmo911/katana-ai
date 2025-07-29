import json
from pathlib import Path

import os
from cryptography.fernet import Fernet

KEY_FILE = Path.home() / ".katana" / "key"

def get_key():
    """
    Gets the encryption key from ~/.katana/key.
    If the key does not exist, it is generated and saved.
    """
    if KEY_FILE.exists():
        with open(KEY_FILE, "rb") as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(KEY_FILE, "wb") as f:
            f.write(key)
        return key

def get_auth_token():
    """
    Gets the auth token from the KATANA_AUTH_TOKEN environment variable or from ~/.katana/cli_auth.json.
    """
    token = os.environ.get("KATANA_AUTH_TOKEN")
    if token:
        return token

    auth_file = Path.home() / ".katana" / "cli_auth.json"
    if not auth_file.exists():
        return None

    with open(auth_file, "r") as f:
        try:
            data = json.load(f)
            encrypted_token = data.get("token")
            if not encrypted_token:
                return None
            key = get_key()
            f = Fernet(key)
            return f.decrypt(encrypted_token.encode()).decode()
        except json.JSONDecodeError:
            return None
