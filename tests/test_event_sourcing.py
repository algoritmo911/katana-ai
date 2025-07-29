import unittest
import os
import shutil
from katana.event_store.event_store import EventStore
from katana.query.graph_projection import GraphProjection

class TestEventSourcing(unittest.TestCase):

    def setUp(self):
        self.db_path = "test_event_store.db"
        self.snapshot_path = "test_snapshots"
        self.event_store = EventStore(self.db_path, self.snapshot_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        if os.path.exists(self.snapshot_path):
            shutil.rmtree(self.snapshot_path)

    def test_event_store_and_projection_with_snapshots(self):
        # Append some events
        self.event_store.append("COMMAND_CREATED", "cmd1", {"type": "type1", "args": {}}, version=1)
        self.event_store.append("COMMAND_STARTED", "cmd1", {}, version=2)

        # Create and build the projection
        projection = GraphProjection(self.event_store)
        projection.build_from_snapshot("cmd1")
        graph = projection.get_graph()

        # Assertions
        self.assertEqual(len(graph), 1)
        self.assertEqual(graph["cmd1"]["status"], "RUNNING")

        # Take a snapshot
        projection.take_snapshot("cmd1")

        # Append more events
        self.event_store.append("COMMAND_COMPLETED", "cmd1", {}, version=3)

        # Create a new projection and build from snapshot
        new_projection = GraphProjection(self.event_store)
        new_projection.build_from_snapshot("cmd1")
        new_graph = new_projection.get_graph()

        # Assertions
        self.assertEqual(len(new_graph), 1)
        self.assertEqual(new_graph["cmd1"]["status"], "DONE")

if __name__ == '__main__':
    unittest.main()
