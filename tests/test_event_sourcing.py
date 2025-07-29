import unittest
import os
from katana.event_store.event_store import EventStore
from katana.query.graph_projection import GraphProjection

class TestEventSourcing(unittest.TestCase):

    def setUp(self):
        self.db_path = "test_event_store.db"
        self.event_store = EventStore(self.db_path)
        self.event_store._load()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_event_store_and_projection(self):
        # Append some events
        self.event_store.append("COMMAND_CREATED", "cmd1", {"type": "type1", "args": {}})
        self.event_store.append("COMMAND_STARTED", "cmd1", {})
        self.event_store.append("COMMAND_CREATED", "cmd2", {"type": "type2", "args": {}})
        self.event_store.append("CHILD_COMMAND_CREATED", "cmd2", {"parent_id": "cmd1"})
        self.event_store.append("COMMAND_COMPLETED", "cmd1", {})

        # Create and build the projection
        projection = GraphProjection(self.event_store)
        projection.build()
        graph = projection.get_graph()

        # Assertions
        self.assertEqual(len(graph), 2)
        self.assertEqual(graph["cmd1"]["status"], "DONE")
        self.assertEqual(graph["cmd2"]["status"], "PENDING")
        self.assertEqual(graph["cmd1"]["children"], ["cmd2"])

if __name__ == '__main__':
    unittest.main()
