import json
from pathlib import Path
from .storage import StorageAdapter

class MockCloudAdapter(StorageAdapter):
    """Storage adapter for a mock cloud storage (a local JSON file)."""

    def __init__(self, remote_db_file: Path = Path('remote_db.json')):
        self.remote_db_file = remote_db_file
        if not self.remote_db_file.exists():
            with open(self.remote_db_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)

    def save(self, user_id: int, data: dict) -> None:
        """Saves user data to the mock cloud storage."""
        with open(self.remote_db_file, 'r+', encoding='utf-8') as f:
            remote_data = json.load(f)
            remote_data[str(user_id)] = data
            f.seek(0)
            json.dump(remote_data, f, indent=4)
            f.truncate()

    def load(self, user_id: int) -> dict | None:
        """Loads user data from the mock cloud storage."""
        with open(self.remote_db_file, 'r', encoding='utf-8') as f:
            remote_data = json.load(f)
        return remote_data.get(str(user_id))

    def list_versions(self, user_id: int) -> list[str]:
        """Lists available versions of a user's profile (not implemented for mock cloud)."""
        return []
