import json
from pathlib import Path
from datetime import datetime, timezone # Added timezone
from typing import Dict, List, Any

DEFAULT_STATE_FILE = Path("katana_state.json")

class ChatHistory:
    def __init__(self):
        self.messages: List[Dict[str, Any]] = []

    def add_message(self, sender: str, text: str, timestamp: str = None):
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).isoformat()
        self.messages.append({"sender": sender, "text": text, "timestamp": timestamp})

    def to_dict(self) -> Dict[str, Any]:
        return {"messages": self.messages}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        history = cls()
        history.messages = data.get("messages", [])
        return history

class KatanaState:
    def __init__(self, state_file_path: Path = DEFAULT_STATE_FILE):
        self.state_file_path: Path = state_file_path
        self.chat_histories: Dict[str, ChatHistory] = {}  # chat_id -> ChatHistory
        self.user_settings: Dict[str, Dict[str, Any]] = {} # chat_id -> settings
        self.global_metrics: Dict[str, Any] = {}
        self._load_state()

    def _load_state(self):
        if self.state_file_path.exists():
            try:
                with open(self.state_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                self.global_metrics = data.get("global_metrics", {})

                for chat_id, history_data in data.get("chat_histories", {}).items():
                    self.chat_histories[chat_id] = ChatHistory.from_dict(history_data)

                self.user_settings = data.get("user_settings", {})
                print(f"Katana state loaded from {self.state_file_path}")
            except json.JSONDecodeError:
                print(f"Error decoding JSON from {self.state_file_path}. Initializing with empty state.")
                self._initialize_empty_state()
            except Exception as e:
                print(f"Could not load state from {self.state_file_path}: {e}. Initializing with empty state.")
                self._initialize_empty_state()
        else:
            print(f"State file {self.state_file_path} not found. Initializing with empty state.")
            self._initialize_empty_state()

    def _initialize_empty_state(self):
        self.chat_histories = {}
        self.user_settings = {}
        self.global_metrics = {"version": "1.0", "last_reset": datetime.now(timezone.utc).isoformat()}
        # Save the initial empty state
        self.save_state()

    def save_state(self):
        data_to_save = {
            "global_metrics": self.global_metrics,
            "chat_histories": {chat_id: history.to_dict() for chat_id, history in self.chat_histories.items()},
            "user_settings": self.user_settings
        }
        try:
            with open(self.state_file_path, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
            # print(f"Katana state saved to {self.state_file_path}")
        except Exception as e:
            print(f"Could not save state to {self.state_file_path}: {e}")

    def get_chat_history(self, chat_id: str) -> ChatHistory:
        chat_id_str = str(chat_id)
        if chat_id_str not in self.chat_histories:
            self.chat_histories[chat_id_str] = ChatHistory()
        return self.chat_histories[chat_id_str]

    def add_chat_message(self, chat_id: str, sender: str, text: str):
        history = self.get_chat_history(chat_id)
        history.add_message(sender, text)
        self.save_state()

    def clear_chat_history(self, chat_id: str):
        chat_id_str = str(chat_id)
        if chat_id_str in self.chat_histories:
            self.chat_histories[chat_id_str] = ChatHistory()
            print(f"Chat history for {chat_id_str} cleared.")
            self.save_state()
        else:
            print(f"No chat history found for {chat_id_str} to clear.")

    def get_user_settings(self, chat_id: str) -> Dict[str, Any]:
        chat_id_str = str(chat_id)
        if chat_id_str not in self.user_settings:
            self.user_settings[chat_id_str] = {"notifications": True, "language": "ru"} # Default settings
        return self.user_settings[chat_id_str]

    def update_user_setting(self, chat_id: str, setting_key: str, setting_value: Any):
        settings = self.get_user_settings(chat_id)
        settings[setting_key] = setting_value
        self.save_state()

    def update_global_metric(self, key: str, value: Any):
        self.global_metrics[key] = value
        self.save_state()

# Example usage:
if __name__ == "__main__":
    # This is for testing the KatanaState class directly
    print("Testing KatanaState...")
    state = KatanaState(Path("test_katana_state.json"))

    # Add some messages
    state.add_chat_message("chat123", "user", "Hello Katana!")
    state.add_chat_message("chat123", "katana", "Hello User!")
    state.add_chat_message("chat456", "user_two", "How are you?")

    # Check history
    history123 = state.get_chat_history("chat123")
    print(f"\nChat 123 History ({len(history123.messages)} messages):")
    for msg in history123.messages:
        print(f"  {msg['sender']} ({msg['timestamp']}): {msg['text']}")

    history456 = state.get_chat_history("chat456")
    print(f"\nChat 456 History ({len(history456.messages)} messages):")
    for msg in history456.messages:
        print(f"  {msg['sender']} ({msg['timestamp']}): {msg['text']}")

    # Settings
    settings123 = state.get_user_settings("chat123")
    print(f"\nChat 123 Settings: {settings123}")
    state.update_user_setting("chat123", "language", "en")
    settings123_updated = state.get_user_settings("chat123")
    print(f"Chat 123 Updated Settings: {settings123_updated}")

    settings_new_user = state.get_user_settings("chat789")
    print(f"Chat 789 (New User) Settings: {settings_new_user}")

    # Global metrics
    print(f"\nGlobal Metrics: {state.global_metrics}")
    state.update_global_metric("total_messages_processed", 100)
    print(f"Updated Global Metrics: {state.global_metrics}")

    # Clear history
    state.clear_chat_history("chat123")
    history123_cleared = state.get_chat_history("chat123")
    print(f"\nChat 123 History after clearing ({len(history123_cleared.messages)} messages).")

    # Test loading from file (by creating a new instance pointing to the same file)
    print("\nTesting loading from file...")
    state_loaded = KatanaState(Path("test_katana_state.json"))
    history456_loaded = state_loaded.get_chat_history("chat456")
    print(f"Chat 456 loaded history has {len(history456_loaded.messages)} messages.")
    print(f"Loaded global metrics: {state_loaded.global_metrics}")
    print(f"Loaded settings for chat123: {state_loaded.get_user_settings('chat123')}") # Should be en

    # Clean up the test file
    # os.remove("test_katana_state.json")
    # print("\nCleaned up test_katana_state.json")
    print("\nTest completed. Check 'test_katana_state.json' file.")
