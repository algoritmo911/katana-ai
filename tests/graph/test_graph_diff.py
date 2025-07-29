import unittest
from katana.graph.command_graph import CommandGraph
from katana.graph.command import Command
from katana.graph.graph_diff import diff_graphs

class TestGraphDiff(unittest.TestCase):

    def test_diff_graphs(self):
        # Create old graph
        old_graph = CommandGraph()
        cmd1_data = {"id": "1", "type": "cmd1", "module": "test", "args": {}}
        cmd2_data = {"id": "2", "type": "cmd2", "module": "test", "args": {}, "parent_id": "1"}
        cmd1 = Command(cmd1_data)
        cmd2 = Command(cmd2_data, parent_id="1")
        old_graph.add_command(cmd1)
        old_graph.add_command(cmd2)

        # Create new graph
        new_graph = CommandGraph()
        cmd1_new_data = {"id": "1", "type": "cmd1", "module": "test", "args": {}}
        cmd3_data = {"id": "3", "type": "cmd3", "module": "test", "args": {}, "parent_id": "1"}
        cmd1_new = Command(cmd1_new_data)
        cmd1_new.status = "DONE"
        cmd3 = Command(cmd3_data, parent_id="1")
        new_graph.add_command(cmd1_new)
        new_graph.add_command(cmd3)

        # Calculate diff
        diff = diff_graphs(old_graph, new_graph)

        # Assertions
        self.assertEqual(len(diff.added), 1)
        self.assertEqual(diff.added[0].id, "3")
        self.assertEqual(len(diff.removed), 1)
        self.assertEqual(diff.removed[0].id, "2")
        self.assertEqual(len(diff.changed), 1)
        self.assertEqual(diff.changed[0].id, "1")
        self.assertEqual(diff.changed[0].status, "DONE")

if __name__ == '__main__':
    unittest.main()
