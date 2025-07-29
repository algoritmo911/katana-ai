import unittest
import os
import shutil
from katana.graph.command_graph import CommandGraph
from katana.graph.snapshot_store import SnapshotStore
from katana.graph.command import Command

class TestSnapshotStore(unittest.TestCase):

    def setUp(self):
        self.store = SnapshotStore("test_snapshots")
        self.graph = CommandGraph()
        self.cmd1_data = {"id": "1", "type": "cmd1", "module": "test", "args": {}}
        self.cmd1 = Command(self.cmd1_data)
        self.graph.add_command(self.cmd1)

    def tearDown(self):
        shutil.rmtree("test_snapshots")

    def test_save_and_load_snapshot(self):
        self.store.save_snapshot(self.graph, "test_snapshot")
        loaded_graph = self.store.load_snapshot("test_snapshot")
        self.assertEqual(len(loaded_graph._commands), 1)
        self.assertEqual(loaded_graph.get_command("1").id, "1")

    def test_list_snapshots(self):
        self.store.save_snapshot(self.graph, "snapshot1")
        self.store.save_snapshot(self.graph, "snapshot2")
        snapshots = self.store.list_snapshots()
        self.assertEqual(len(snapshots), 2)
        self.assertIn("snapshot1", snapshots)
        self.assertIn("snapshot2", snapshots)

if __name__ == '__main__':
    unittest.main()
