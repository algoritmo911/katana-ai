import json
from pathlib import Path
from datetime import datetime

HISTORY_DIR = Path('chat_history')
HISTORY_DIR.mkdir(parents=True, exist_ok=True)

class ChatHistory:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.history_file = HISTORY_DIR / f"{self.chat_id}_history.json"
        self.messages = self._load_history()

    def _load_history(self):
        if self.history_file.exists():
            with open(self.history_file, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return []
        return []

    def _save_history(self):
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.messages, f, ensure_ascii=False, indent=2)

    def add_message(self, user, text, timestamp=None):
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat()

        self.messages.append({
            "user": user,
            "text": text,
            "timestamp": timestamp
        })
        self._save_history()

    def get_history(self, limit=None):
        if limit:
            return self.messages[-limit:]
        return self.messages

    def clear_history(self):
        self.messages = []
        self._save_history()
