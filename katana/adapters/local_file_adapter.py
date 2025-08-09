import json
from pathlib import Path
from katana.core.user_profile import UserProfile
from .storage import StorageAdapter

class LocalFileAdapter(StorageAdapter):
    """Storage adapter for the local filesystem."""

    def __init__(self, user_data_dir: Path = Path('user_data')):
        self.user_data_dir = user_data_dir
        self.user_data_dir.mkdir(parents=True, exist_ok=True)

    def save(self, user_id: int, data: dict) -> None:
        """Saves user data to a local JSON file."""
        profile_path = self.user_data_dir / f"{user_id}.json"
        with open(profile_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def load(self, user_id: int) -> dict | None:
        """Loads user data from a local JSON file."""
        profile_path = self.user_data_dir / f"{user_id}.json"
        if not profile_path.exists():
            return None
        with open(profile_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def list_versions(self, user_id: int) -> list[str]:
        """Lists available versions of a user's profile (not implemented for local files)."""
        return []
