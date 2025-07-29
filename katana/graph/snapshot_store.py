import os
import json
from .command_graph import CommandGraph

class SnapshotStore:
    def __init__(self, base_path="snapshots"):
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)

    def save_snapshot(self, graph, name):
        path = os.path.join(self.base_path, f"{name}.json")
        graph.save_to_file(path)

    def load_snapshot(self, name):
        path = os.path.join(self.base_path, f"{name}.json")
        graph = CommandGraph()
        graph.load_from_file(path)
        return graph

    def list_snapshots(self):
        return [f.replace(".json", "") for f in os.listdir(self.base_path) if f.endswith(".json")]
