import unittest
from command_graph import Command, CommandGraph

class TestCommandGraph(unittest.TestCase):

    def test_command_creation(self):
        command_data = {"id": "1", "type": "test", "module": "test_module", "args": {}}
        command = Command(command_data)
        self.assertEqual(command.id, "1")
        self.assertEqual(command.type, "test")
        self.assertEqual(command.module, "test_module")
        self.assertEqual(command.args, {})
        self.assertIsNone(command.parent_id)
        self.assertEqual(command.children_ids, [])

    def test_command_creation_with_parent(self):
        command_data = {"id": "2", "type": "child_test", "module": "test_module", "args": {}}
        command = Command(command_data, parent_id="1")
        self.assertEqual(command.id, "2")
        self.assertEqual(command.parent_id, "1")

    def test_add_child(self):
        command_data = {"id": "1", "type": "parent", "module": "test_module", "args": {}}
        command = Command(command_data)
        command.add_child("2")
        self.assertEqual(command.children_ids, ["2"])
        command.add_child("3")
        self.assertEqual(command.children_ids, ["2", "3"])
        command.add_child("2") # Should not add duplicates
        self.assertEqual(command.children_ids, ["2", "3"])

    def test_graph_add_command(self):
        graph = CommandGraph()
        command_data = {"id": "1", "type": "test", "module": "test_module", "args": {}}
        command = Command(command_data)
        graph.add_command(command)
        self.assertEqual(graph.get_command("1"), command)

    def test_graph_add_child_command(self):
        graph = CommandGraph()
        parent_data = {"id": "1", "type": "parent", "module": "test_module", "args": {}}
        parent_command = Command(parent_data)
        graph.add_command(parent_command)

        child_data = {"id": "2", "type": "child", "module": "test_module", "args": {}}
        child_command = Command(child_data, parent_id="1")
        graph.add_command(child_command)

        self.assertEqual(parent_command.children_ids, ["2"])
        self.assertEqual(child_command.parent_id, "1")

    def test_to_dot(self):
        graph = CommandGraph()
        parent_data = {"id": "1", "type": "parent", "module": "test_module", "args": {}}
        parent_command = Command(parent_data)
        graph.add_command(parent_command)

        child_data = {"id": "2", "type": "child", "module": "test_module", "args": {}, "parent_id": "1"}
        child_command = Command(child_data, parent_id="1")
        graph.add_command(child_command)

        dot_string = graph.to_dot()
        self.assertIn('digraph CommandGraph {', dot_string)
        self.assertIn('"1" [label="ID: 1\\nType: parent\\nModule: test_module"];', dot_string)
        self.assertIn('"2" [label="ID: 2\\nType: child\\nModule: test_module"];', dot_string)
        self.assertIn('"1" -> "2";', dot_string)
        self.assertIn("}", dot_string)

if __name__ == '__main__':
    unittest.main()
