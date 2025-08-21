# -*- coding: utf-8 -*-
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
    """
    def __init__(self):
        self._graph = MOCK_MEMORY_GRAPH

    def run_query(self, query: str, memory_id: str):
        """
        Simulates running a query. For now, it ignores the query text and
        the memory_id and just returns the entire mock graph.
        In a real implementation, this would parse the Cypher query and
        traverse the graph.
        """
        print(f"MockNeurovaultDriver: Running query for memory_id '{memory_id}'...")
        # A real implementation would return a list of records.
        # We will just return the raw graph for the Incarnator to process.
        return self._graph

    def close(self):
        """Simulates closing the connection."""
        print("MockNeurovaultDriver: Connection closed.")

def get_driver():
    """Factory function to get the mock driver."""
    return MockNeurovaultDriver()
