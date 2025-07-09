import unittest
import subprocess
import json
from katana.proportions import set_proportions, get_proportions, get_recommendations, PROPORTIONS

class TestProportionsModule(unittest.TestCase):

    def setUp(self):
        # Reset proportions before each test
        PROPORTIONS["nodes"] = 1/3
        PROPORTIONS["tasks"] = 1/3
        PROPORTIONS["memory"] = 1/3

    def test_set_proportions_valid(self):
        set_proportions(nodes=0.5, tasks=0.3, memory=0.2)
        current_proportions = get_proportions()
        self.assertAlmostEqual(current_proportions["nodes"], 0.5)
        self.assertAlmostEqual(current_proportions["tasks"], 0.3)
        self.assertAlmostEqual(current_proportions["memory"], 0.2)

    def test_set_proportions_zero_total(self):
        set_proportions(nodes=0, tasks=0, memory=0)
        current_proportions = get_proportions()
        self.assertAlmostEqual(current_proportions["nodes"], 1/3)
        self.assertAlmostEqual(current_proportions["tasks"], 1/3)
        self.assertAlmostEqual(current_proportions["memory"], 1/3)

    def test_set_proportions_negative_values(self):
        with self.assertRaises(ValueError):
            set_proportions(nodes=-0.5, tasks=0.3, memory=0.2)
        with self.assertRaises(ValueError):
            set_proportions(nodes=0.5, tasks=-0.3, memory=0.2)
        with self.assertRaises(ValueError):
            set_proportions(nodes=0.5, tasks=0.3, memory=-0.2)

    def test_get_proportions(self):
        # Default proportions
        props = get_proportions()
        self.assertAlmostEqual(props["nodes"], 1/3)
        self.assertAlmostEqual(props["tasks"], 1/3)
        self.assertAlmostEqual(props["memory"], 1/3)

        # Set new proportions
        set_proportions(nodes=0.6, tasks=0.2, memory=0.2)
        new_props = get_proportions()
        self.assertAlmostEqual(new_props["nodes"], 0.6)
        self.assertAlmostEqual(new_props["tasks"], 0.2)
        self.assertAlmostEqual(new_props["memory"], 0.2)

    def test_get_recommendations(self):
        set_proportions(nodes=0.5, tasks=0.3, memory=0.2)
        total_resources = {"nodes": 100, "tasks": 200, "memory_gb": 512}
        recommendations = get_recommendations(total_resources)

        self.assertEqual(recommendations["nodes"], 50) # 100 * 0.5
        self.assertEqual(recommendations["tasks"], 60) # 200 * 0.3
        self.assertAlmostEqual(recommendations["memory_gb"], 102.4) # 512 * 0.2

    def test_get_recommendations_partial_resources(self):
        set_proportions(nodes=0.5, tasks=0.25, memory=0.25)
        total_resources = {"nodes": 100, "memory_gb": 200} # tasks missing
        recommendations = get_recommendations(total_resources)

        self.assertEqual(recommendations["nodes"], 50)
        self.assertNotIn("tasks", recommendations)
        self.assertAlmostEqual(recommendations["memory_gb"], 50.0)

    def test_proportions_normalization(self):
        set_proportions(nodes=1, tasks=1, memory=2) # Total = 4
        props = get_proportions()
        self.assertAlmostEqual(props["nodes"], 0.25) # 1/4
        self.assertAlmostEqual(props["tasks"], 0.25) # 1/4
        self.assertAlmostEqual(props["memory"], 0.50)  # 2/4


class TestProportionsCLI(unittest.TestCase):

    def run_katana_command(self, command):
        """Helper function to run katana CLI commands."""
        # Ensure using the project's katana_cli.py
        base_command = ["python", "katana_cli.py"]
        full_command = base_command + command
        result = subprocess.run(full_command, capture_output=True, text=True, check=False)
        return result

    def setUp(self):
        # No setup needed that persists across CLI calls, as each is a new process.
        # katana.proportions will initialize with its defaults.
        pass

    def test_cli_set_proportions_output(self):
        # Tests that the 'set' command itself outputs the new proportions correctly.
        result = self.run_katana_command(["proportions", "set", "--nodes", "0.6", "--tasks", "0.2", "--memory", "0.2"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("Proportions updated successfully.", result.stdout)
        self.assertIn("Current normalized proportions: Nodes: 0.60, Tasks: 0.20, Memory: 0.20", result.stdout)

    def test_cli_set_proportions_invalid(self):
        result = self.run_katana_command(["proportions", "set", "--nodes", "-0.5", "--tasks", "0.3", "--memory", "0.2"])
        self.assertEqual(result.returncode, 0) # The script itself doesn't exit with error, but prints error
        self.assertIn("Error: Proportions must be non-negative.", result.stdout)

    def test_cli_get_proportions_default(self):
        # Tests that 'get' command shows the default normalized proportions
        result = self.run_katana_command(["proportions", "get"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("Current proportions: Nodes: 0.33, Tasks: 0.33, Memory: 0.33", result.stdout)

    def test_cli_recommend_with_default_proportions_and_totals(self):
        # Tests 'recommend' with default proportions and default total resources
        result = self.run_katana_command(["proportions", "recommend"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("Based on current proportions:", result.stdout)
        self.assertIn("Nodes: 0.33", result.stdout) # Default proportion
        self.assertIn("Tasks: 0.33", result.stdout) # Default proportion
        self.assertIn("Memory: 0.33", result.stdout) # Default proportion
        # Default totals: nodes=100, tasks=200, memory_gb=256
        # Recommendations: nodes = 100*0.3333.. = 33, tasks = 200*0.3333.. = 67, memory = 256*0.3333.. = 85.33
        self.assertIn("Recommended Nodes: 33 (out of 100 total)", result.stdout)
        self.assertIn("Recommended Tasks: 67 (out of 200 total)", result.stdout)
        self.assertIn("Recommended Memory: 85.33 GB (out of 256.0 GB total)", result.stdout)

    def test_cli_recommend_with_default_proportions_custom_totals(self):
        # Tests 'recommend' with default proportions and custom total resources
        result = self.run_katana_command([
            "proportions", "recommend",
            "--total-nodes", "40",
            "--total-tasks", "80",
            "--total-memory-gb", "128.0"
        ])
        self.assertEqual(result.returncode, 0)
        self.assertIn("Based on current proportions:", result.stdout)
        self.assertIn("Nodes: 0.33", result.stdout) # Default proportion
        self.assertIn("Tasks: 0.33", result.stdout) # Default proportion
        self.assertIn("Memory: 0.33", result.stdout) # Default proportion
        # Custom totals: nodes=40, tasks=80, memory_gb=128
        # Recommendations: nodes = 40*0.3333.. = 13, tasks = 80*0.3333.. = 27, memory = 128*0.3333.. = 42.67
        self.assertIn("Recommended Nodes: 13 (out of 40 total)", result.stdout)
        self.assertIn("Recommended Tasks: 27 (out of 80 total)", result.stdout)
        self.assertIn("Recommended Memory: 42.67 GB (out of 128.0 GB total)", result.stdout)

    def test_cli_recommend_with_override_proportions(self):
        # This test will call 'recommend' and provide proportions arguments,
        # which should override the defaults for that single command.
        result = self.run_katana_command([
            "proportions", "recommend",
            "--total-nodes", "100",
            "--total-tasks", "100",
            "--total-memory-gb", "100.0",
            "--nodes", "0.1", # Override
            "--tasks", "0.1", # Override
            "--memory", "0.8"  # Override
        ])
        self.assertEqual(result.returncode, 0)
        self.assertIn("Using provided proportions for this recommendation.", result.stdout)
        self.assertIn("Nodes: 0.10", result.stdout) # Checking the proportion used for recommendation
        self.assertIn("Tasks: 0.10", result.stdout)
        self.assertIn("Memory: 0.80", result.stdout)
        self.assertIn("Recommended Nodes: 10 (out of 100 total)", result.stdout) # 100 * 0.1
        self.assertIn("Recommended Tasks: 10 (out of 100 total)", result.stdout) # 100 * 0.1
        self.assertIn("Recommended Memory: 80.00 GB (out of 100.0 GB total)", result.stdout) # 100 * 0.8

        # Verify that the default proportions were NOT changed by the override in recommend
        result_get = self.run_katana_command(["proportions", "get"])
        self.assertEqual(result_get.returncode, 0)
        # Should still be the default proportions
        self.assertIn("Current proportions: Nodes: 0.33, Tasks: 0.33, Memory: 0.33", result_get.stdout)

if __name__ == '__main__':
    unittest.main()
