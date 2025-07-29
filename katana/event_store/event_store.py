import json
import os
from datetime import datetime
from typing import List, Dict, Any

class EventStore:
    def __init__(self, db_path="event_store.db", snapshot_path="snapshots"):
        self.db_path = db_path
        self.snapshot_path = snapshot_path
        os.makedirs(self.snapshot_path, exist_ok=True)
        self.db = []
        self._load()

    def append(self, event_type: str, aggregate_id: str, payload: Dict[str, Any], version: int = 1):
        event = {
            "event_type": event_type,
            "aggregate_id": aggregate_id,
            "payload": payload,
            "timestamp": datetime.now().isoformat(),
            "version": version,
        }
        self.db.append(event)
        self._commit()

    def get_events_for_aggregate(self, aggregate_id: str) -> List[Dict[str, Any]]:
        snapshot, last_version = self._load_snapshot(aggregate_id)
        events = [
            event
            for event in self.db
            if event["aggregate_id"] == aggregate_id and event["version"] > last_version
        ]
        return snapshot, events

    def _commit(self):
        with open(self.db_path, "w") as f:
            json.dump(self.db, f, indent=2)

    def _load(self):
        try:
            with open(self.db_path, "r") as f:
                self.db = json.load(f)
        except FileNotFoundError:
            self.db = []

    def take_snapshot(self, aggregate_id: str, aggregate_state: Dict[str, Any], last_version: int):
        snapshot_file = os.path.join(self.snapshot_path, f"{aggregate_id}.json")
        with open(snapshot_file, "w") as f:
            json.dump({"state": aggregate_state, "version": last_version}, f, indent=2)

    def _load_snapshot(self, aggregate_id: str) -> (Dict[str, Any], int):
        snapshot_file = os.path.join(self.snapshot_path, f"{aggregate_id}.json")
        try:
            with open(snapshot_file, "r") as f:
                snapshot = json.load(f)
                return snapshot["state"], snapshot["version"]
        except FileNotFoundError:
            return None, 0
