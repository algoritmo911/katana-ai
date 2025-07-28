import unittest
import os
import json
from katana.graph.command import Command
from katana.graph.command_graph import CommandGraph

class TestCommandGraph(unittest.TestCase):

    def setUp(self):
        self.graph = CommandGraph()
        self.cmd1_data = {"id": "1", "type": "cmd1", "module": "test", "args": {}}
        self.cmd2_data = {"id": "2", "type": "cmd2", "module": "test", "args": {}, "parent_id": "1"}
        self.cmd3_data = {"id": "3", "type": "cmd3", "module": "test", "args": {}, "parent_id": "1"}
        self.cmd4_data = {"id": "4", "type": "cmd4", "module": "test", "args": {}}

        self.cmd1 = Command(self.cmd1_data)
        self.cmd2 = Command(self.cmd2_data, parent_id="1")
        self.cmd3 = Command(self.cmd3_data, parent_id="1")
        self.cmd4 = Command(self.cmd4_data)

        self.graph.add_command(self.cmd1)
        self.graph.add_command(self.cmd2)
        self.graph.add_command(self.cmd3)
        self.graph.add_command(self.cmd4)

    def test_add_command(self):
        self.assertEqual(len(self.graph._commands), 4)
        self.assertEqual(self.graph.get_command("1"), self.cmd1)
        self.assertEqual(self.graph.get_command("2"), self.cmd2)
        self.assertEqual(self.graph.get_command("3"), self.cmd3)
        self.assertEqual(self.graph.get_command("4"), self.cmd4)
        self.assertEqual(self.cmd1.children_ids, ["2", "3"])

    def test_get_roots(self):
        roots = self.graph.get_roots()
        self.assertEqual(len(roots), 2)
        self.assertIn(self.cmd1, roots)
        self.assertIn(self.cmd4, roots)

    def test_get_by_status(self):
        self.cmd1.status = "DONE"
        self.cmd2.status = "ERROR"
        self.cmd3.status = "DONE"
        self.cmd4.status = "RUNNING"

        done_cmds = self.graph.get_by_status("DONE")
        self.assertEqual(len(done_cmds), 2)
        self.assertIn(self.cmd1, done_cmds)
        self.assertIn(self.cmd3, done_cmds)

        error_cmds = self.graph.get_by_status("ERROR")
        self.assertEqual(len(error_cmds), 1)
        self.assertIn(self.cmd2, error_cmds)

        running_cmds = self.graph.get_by_status("RUNNING")
        self.assertEqual(len(running_cmds), 1)
        self.assertIn(self.cmd4, running_cmds)

    def test_save_and_load_from_file(self):
        path = "test_graph.json"
        self.graph.save_to_file(path)

        new_graph = CommandGraph()
        new_graph.load_from_file(path)

        self.assertEqual(len(new_graph._commands), 4)
        self.assertEqual(new_graph.get_command("1").id, self.cmd1.id)
        self.assertEqual(new_graph.get_command("2").parent_id, "1")
        self.assertEqual(new_graph.get_command("1").children_ids, ["2", "3"])

        os.remove(path)

if __name__ == '__main__':
    unittest.main()
