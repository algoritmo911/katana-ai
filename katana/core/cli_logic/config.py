import json
from pathlib import Path

CONFIG_FILE = Path.home() / ".katana" / "config.json"

def get_config():
    """
    Gets the config from ~/.katana/config.json.
    """
    if not CONFIG_FILE.exists():
        return {}

    with open(CONFIG_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

from katana.core.auth import get_key
from cryptography.fernet import Fernet

def set_config_value(key, value):
    """
    Sets a config value in ~/.katana/config.json.
    """
    config = get_config()
    if key == "token":
        encryption_key = get_key()
        f = Fernet(encryption_key)
        encrypted_token = f.encrypt(value.encode()).decode()
        config[key] = encrypted_token
    else:
        config[key] = value
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def show_config():
    """
    Returns the current config.
    """
    return get_config()
