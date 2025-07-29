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

def set_config_value(key, value):
    """
    Sets a config value in ~/.katana/config.json.
    """
    config = get_config()
    config[key] = value
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def show_config():
    """
    Returns the current config.
    """
    return get_config()
