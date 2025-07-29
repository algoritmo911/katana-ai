import unittest
import os
from click.testing import CliRunner
from katana.cli.graph import graph

class TestCliGraph(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()
        self.graph_file = "test_graph.json"
        with open(self.graph_file, "w") as f:
            f.write("""
[
  {
    "id": "1",
    "type": "cmd1",
    "module": "test",
    "args": {},
    "started_at": "2024-01-01T00:00:00",
    "finished_at": null,
    "status": "RUNNING",
    "parent_id": null,
    "children_ids": [
      "2"
    ]
  },
  {
    "id": "2",
    "type": "cmd2",
    "module": "test",
    "args": {},
    "started_at": "2024-01-01T00:01:00",
    "finished_at": null,
    "status": "ERROR",
    "parent_id": "1",
    "children_ids": []
  }
]
""")

    def tearDown(self):
        os.remove(self.graph_file)

    def test_show_rich(self):
        result = self.runner.invoke(graph, ["show", "--path", self.graph_file, "--format", "rich"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("cmd1", result.output)
        self.assertIn("cmd2", result.output)

    def test_show_dot(self):
        result = self.runner.invoke(graph, ["show", "--path", self.graph_file, "--format", "dot"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("digraph CommandGraph", result.output)
        self.assertIn('"1" -> "2"', result.output)


    def test_errors(self):
        result = self.runner.invoke(graph, ["errors", "--path", self.graph_file])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("ID: 2", result.output)
        self.assertNotIn("ID: 1", result.output)

    def test_trace(self):
        result = self.runner.invoke(graph, ["trace", "2", "--path", self.graph_file])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.output.strip(), "1 -> 2")

if __name__ == '__main__':
    unittest.main()
