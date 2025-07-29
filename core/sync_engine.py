import json
import hashlib
from pathlib import Path

USER_DATA_DIR = Path('user_data')
REMOTE_DB_FILE = Path('remote_db.json')

def _get_local_profile_hash(user_id: int) -> str | None:
    """Calculates the SHA256 hash of the local user profile."""
    profile_path = USER_DATA_DIR / f"{user_id}.json"
    if not profile_path.exists():
        return None
    with open(profile_path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def _get_remote_profile_hash(user_id: int) -> str | None:
    """Gets the SHA256 hash of the remote user profile."""
    if not REMOTE_DB_FILE.exists():
        return None
    with open(REMOTE_DB_FILE, 'r', encoding='utf-8') as f:
        remote_data = json.load(f)
    return remote_data.get(str(user_id), {}).get('hash')

def push_profile_to_cloud(user_id: int):
    """Pushes the user profile to the mock cloud storage."""
    profile_path = USER_DATA_DIR / f"{user_id}.json"
    if not profile_path.exists():
        raise FileNotFoundError(f"Profile for user {user_id} not found.")

    with open(profile_path, 'r', encoding='utf-8') as f:
        profile_data = json.load(f)

    if not REMOTE_DB_FILE.exists():
        with open(REMOTE_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)

    with open(REMOTE_DB_FILE, 'r+', encoding='utf-8') as f:
        remote_data = json.load(f)
        remote_data[str(user_id)] = {
            "data": profile_data,
            "hash": _get_local_profile_hash(user_id)
        }
        f.seek(0)
        json.dump(remote_data, f, indent=4)
        f.truncate()

def pull_profile_from_cloud(user_id: int):
    """Pulls the user profile from the mock cloud storage."""
    if not REMOTE_DB_FILE.exists():
        raise FileNotFoundError("Remote database not found.")

    with open(REMOTE_DB_FILE, 'r', encoding='utf-8') as f:
        remote_data = json.load(f)

    user_profile_data = remote_data.get(str(user_id), {}).get('data')
    if not user_profile_data:
        raise ValueError(f"Profile for user {user_id} not found in remote database.")

    profile_path = USER_DATA_DIR / f"{user_id}.json"
    with open(profile_path, 'w', encoding='utf-8') as f:
        json.dump(user_profile_data, f, indent=4)

def get_sync_status(user_id: int) -> str:
    """Gets the sync status of the user profile."""
    local_hash = _get_local_profile_hash(user_id)
    remote_hash = _get_remote_profile_hash(user_id)

    if not local_hash and not remote_hash:
        return "not found"
    if not local_hash:
        return "remote only"
    if not remote_hash:
        return "local only"
    if local_hash == remote_hash:
        return "in sync"
    return "conflict"
