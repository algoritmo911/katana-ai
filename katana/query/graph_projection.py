from typing import List, Dict, Any

class GraphProjection:
    def __init__(self, event_store):
        self.event_store = event_store
        self.graph = {}

    def build(self):
        events = self.event_store.db # In a real implementation, this would stream events
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

    def get_graph(self) -> Dict[str, Any]:
        return self.graph
