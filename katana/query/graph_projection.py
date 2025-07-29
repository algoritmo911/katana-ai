from typing import List, Dict, Any

class GraphProjection:
    def __init__(self, event_store):
        self.event_store = event_store
        self.graph = {}
        self.version = 0

    def build_from_snapshot(self, aggregate_id: str):
        snapshot, events = self.event_store.get_events_for_aggregate(aggregate_id)
        if snapshot:
            self.graph = snapshot
            self.version = self.event_store._load_snapshot(aggregate_id)[1]

        self.apply_events(events)

    def apply_events(self, events: List[Dict[str, Any]]):
        for event in events:
            if event["event_type"] == "COMMAND_CREATED":
                self.graph[event["aggregate_id"]] = {
                    "id": event["aggregate_id"],
                    "type": event["payload"]["type"],
                    "args": event["payload"]["args"],
                    "status": "PENDING",
                    "children": [],
                }
            elif event["event_type"] == "COMMAND_STARTED":
                if event["aggregate_id"] in self.graph:
                    self.graph[event["aggregate_id"]]["status"] = "RUNNING"
            elif event["event_type"] == "COMMAND_COMPLETED":
                if event["aggregate_id"] in self.graph:
                    self.graph[event["aggregate_id"]]["status"] = "DONE"
            elif event["event_type"] == "COMMAND_FAILED":
                if event["aggregate_id"] in self.graph:
                    self.graph[event["aggregate_id"]]["status"] = "ERROR"
            elif event["event_type"] == "CHILD_COMMAND_CREATED":
                parent_id = event["payload"]["parent_id"]
                child_id = event["aggregate_id"]
                if parent_id in self.graph:
                    self.graph[parent_id]["children"].append(child_id)

            self.version = event["version"]

    def get_graph(self) -> Dict[str, Any]:
        return self.graph

    def take_snapshot(self, aggregate_id: str):
        self.event_store.take_snapshot(aggregate_id, self.graph, self.version)
