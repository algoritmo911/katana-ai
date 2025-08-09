import json
import hashlib
from katana.adapters.storage import StorageAdapter
from katana.core.user_profile import UserProfile

def _get_profile_hash(data: dict) -> str:
    """Calculates the SHA256 hash of the profile data."""
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode('utf-8')).hexdigest()

class SyncEngine:
    def __init__(self, local_storage: StorageAdapter, remote_storage: StorageAdapter):
        self.local_storage = local_storage
        self.remote_storage = remote_storage

    def push(self, user_id: int):
        """Pushes the user profile to the remote storage."""
        local_profile_data = self.local_storage.load(user_id)
        if not local_profile_data:
            raise FileNotFoundError(f"Local profile for user {user_id} not found.")

        self.remote_storage.save(user_id, local_profile_data)

    def pull(self, user_id: int):
        """Pulls the user profile from the remote storage."""
        remote_profile_data = self.remote_storage.load(user_id)
        if not remote_profile_data:
            raise FileNotFoundError(f"Remote profile for user {user_id} not found.")

        self.local_storage.save(user_id, remote_profile_data)

    def get_sync_status(self, user_id: int) -> str:
        """Gets the sync status of the user profile."""
        local_profile_data = self.local_storage.load(user_id)
        remote_profile_data = self.remote_storage.load(user_id)

        if not local_profile_data and not remote_profile_data:
            return "not found"
        if not local_profile_data:
            return "remote only"
        if not remote_profile_data:
            return "local only"

        local_hash = _get_profile_hash(local_profile_data)
        remote_hash = _get_profile_hash(remote_profile_data)

        if local_hash == remote_hash:
            return "in sync"
        return "conflict"
