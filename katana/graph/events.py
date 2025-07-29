from dataclasses import dataclass, asdict
from datetime import datetime
import json
from typing import Literal, Dict, Any, List

@dataclass
class GraphEvent:
    type: Literal["ADD_NODE", "REMOVE_NODE", "UPDATE_STATUS", "ADD_EDGE", "REMOVE_EDGE"]
    timestamp: datetime
    payload: Dict[str, Any]

    def to_json(self):
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return json.dumps(data)

    @classmethod
    def from_json(cls, json_str):
        data = json.loads(json_str)
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)

class EventLog:
    def __init__(self, path="event_log.jsonl"):
        self.path = path

    def log_event(self, event: GraphEvent):
        with open(self.path, "a") as f:
            f.write(event.to_json() + "\n")

    def read_events(self) -> List[GraphEvent]:
        events = []
        with open(self.path, "r") as f:
            for line in f:
                events.append(GraphEvent.from_json(line))
        return events
