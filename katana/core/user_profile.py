from dataclasses import dataclass, field
from datetime import datetime
from collections import Counter

@dataclass
class UserProfile:
    user_id: int
    command_history: list[dict] = field(default_factory=list)
    preferences: dict = field(default_factory=dict)
    last_seen: str | None = None

    def add_command_to_history(self, command: str):
        """Adds a command to the user's command history."""
        self.command_history.append({
            "command": command,
            "timestamp": datetime.utcnow().isoformat()
        })

    def get_command_recommendations(self, top_n: int = 3) -> list[str]:
        """Gets the top N most frequent commands from the user's history."""
        if not self.command_history:
            return []

        command_counter = Counter(item['command'] for item in self.command_history)
        most_common = command_counter.most_common(top_n)
        return [command for command, count in most_common]
