import json
from datetime import datetime
from typing import List, Dict, Any

class EventStore:
    def __init__(self, db_path="event_store.db"):
        self.db_path = db_path
        # In a real implementation, this would be a connection to a database.
        # For now, we'll just use a file.
        self.db = []

    def append(self, event_type: str, aggregate_id: str, payload: Dict[str, Any]):
        event = {
            "event_type": event_type,
            "aggregate_id": aggregate_id,
            "payload": payload,
            "timestamp": datetime.now().isoformat(),
        }
        self.db.append(event)
        self._commit()

    def get_events_for_aggregate(self, aggregate_id: str) -> List[Dict[str, Any]]:
        return [event for event in self.db if event["aggregate_id"] == aggregate_id]

    def _commit(self):
        with open(self.db_path, "w") as f:
            json.dump(self.db, f, indent=2)

    def _load(self):
        try:
            with open(self.db_path, "r") as f:
                self.db = json.load(f)
        except FileNotFoundError:
            self.db = []
