import unittest
import sys
import os

# Add project root to sys.path to allow importing katana module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from katana.self_evolve import SelfEvolver


class TestSelfEvolver(unittest.TestCase):

    def setUp(self):
        """Set up for test methods."""
        self.evolver = SelfEvolver()

    def test_generate_patch_not_empty(self):
        """
        Test that generate_patch returns a non-empty string for a given task description.
        """
        task_description = "Implement a test feature"
        patch = self.evolver.generate_patch(task_description)
        self.assertIsInstance(patch, str, "Patch should be a string.")
        self.assertTrue(len(patch) > 0, "Generated patch should not be empty.")
        self.assertIn(
            task_description, patch, "Task description should be in the patch."
        )

    def test_run_tests_mock(self):
        """
        Test the mock run_tests method.
        It should currently always return True.
        """
        dummy_patch = "# This is a dummy patch"
        result = self.evolver.run_tests(dummy_patch)
        self.assertTrue(result, "run_tests mock should return True.")

    def test_apply_patch_mock(self):
        """
        Test the mock apply_patch method.
        It should currently always return True.
        """
        dummy_patch = "# This is a dummy patch"
        result = self.evolver.apply_patch(dummy_patch)
        self.assertTrue(result, "apply_patch mock should return True.")


if __name__ == "__main__":
    unittest.main()
