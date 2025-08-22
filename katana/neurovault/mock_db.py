# -*- coding: utf-8 -*-
import copy
"""
Mock Neurovault Database and Driver.

This file simulates the 'neurovault' graph database for development
and testing purposes without needing a live Neo4j instance.
"""

# --- Mock Database ---
# A simple graph structure representing a memory.
# The format is a dictionary of nodes and a list of relationships.
MOCK_MEMORY_GRAPH = {
    "nodes": {
        "person_a": {"labels": ["Person"], "properties": {"name": "Alex", "mood": "happy"}},
        "person_b": {"labels": ["Person"], "properties": {"name": "Sam"}}, # Mood is missing
        "object_1": {"labels": ["Object", "Key"], "properties": {"type": "metal"}},
        "object_2": {"labels": ["Object", "Door"], "properties": {"state": "closed"}},
        "location_1": {"labels": ["Location"], "properties": {"name": "Hallway"}},
    },
    "relationships": [
        {"from": "person_a", "to": "object_1", "type": "USED"},
        {"from": "object_1", "to": "object_2", "type": "OPENS"},
        {"from": "person_a", "to": "location_1", "type": "IS_IN"},
        {"from": "person_b", "to": "location_1", "type": "IS_IN"},
        {"from": "object_2", "to": "location_1", "type": "IS_IN"},
    ]
}

# --- Mock Driver ---

class MockNeurovaultDriver:
    """
    A mock driver that simulates running Cypher queries against the mock graph.
    It now supports simulated write transactions to test the Reconciler.
    """
    def __init__(self):
        # Use deepcopy to ensure the base graph isn't modified by tests
        self._graph = copy.deepcopy(MOCK_MEMORY_GRAPH)

    def run_query(self, query: str, memory_id: str):
        """
        Simulates running a read query. For now, it just returns the graph.
        """
        print(f"MockNeurovaultDriver: Running read query for memory_id '{memory_id}'...")
        return self._graph

    def run_write_transaction(self, commands: list):
        """
        Simulates a write transaction by processing a list of commands.
        """
        print(f"MockNeurovaultDriver: Running write transaction with {len(commands)} commands...")
        for command in commands:
            action = command.get("action")
            if action == "CREATE_NODE":
                node_id = command.get("node_id")
                if node_id in self._graph["nodes"]:
                    raise ValueError(f"Node {node_id} already exists.")
                self._graph["nodes"][node_id] = command.get("data")
            elif action == "CREATE_RELATIONSHIP":
                self._graph["relationships"].append(command.get("data"))
            else:
                raise ValueError(f"Unknown write action: {action}")
        print("MockNeurovaultDriver: Write transaction complete.")

    def dump_graph(self):
        """Returns the current state of the entire graph."""
        return self._graph

    def close(self):
        """Simulates closing the connection."""
        print("MockNeurovaultDriver: Connection closed.")

def get_driver():
    """Factory function to get the mock driver."""
    return MockNeurovaultDriver()
