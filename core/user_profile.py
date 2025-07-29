import json
import os
from pathlib import Path
from datetime import datetime
from collections import Counter

USER_DATA_DIR = Path('user_data')
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

class UserProfile:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.profile_path = USER_DATA_DIR / f"{user_id}.json"
        self.data = {
            "user_id": self.user_id,
            "command_history": [],
            "preferences": {},
            "last_seen": None
        }
        self.load()

    def load(self):
        """Loads the user profile from a JSON file."""
        if self.profile_path.exists():
            with open(self.profile_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)

    def save(self):
        """Saves the user profile to a JSON file."""
        self.data['last_seen'] = datetime.utcnow().isoformat()
        with open(self.profile_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def add_command_to_history(self, command: str):
        """Adds a command to the user's command history."""
        self.data['command_history'].append({
            "command": command,
            "timestamp": datetime.utcnow().isoformat()
        })

    def get_command_recommendations(self, top_n: int = 3) -> list[str]:
        """Gets the top N most frequent commands from the user's history."""
        if not self.data['command_history']:
            return []

        command_counter = Counter(item['command'] for item in self.data['command_history'])
        most_common = command_counter.most_common(top_n)
        return [command for command, count in most_common]

def get_user_profile(user_id: int) -> UserProfile:
    """Factory function to get a user profile instance."""
    return UserProfile(user_id)
