import unittest
import os
import sys
from io import StringIO
from unittest.mock import patch

# Add the 'core' directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'core'))

from core.dao_core import DaoCore

class TestDaoCore(unittest.TestCase):

    def setUp(self):
        """Set up the test environment."""
        self.constitution_path = os.path.join(os.path.dirname(__file__), 'core', 'constitution.yaml')
        # Ensure a constitution file exists for the test
        if not os.path.exists(self.constitution_path):
            os.makedirs(os.path.dirname(self.constitution_path), exist_ok=True)
            with open(self.constitution_path, 'w') as f:
                f.write("""
goal: "maximize_knowledge_connectivity"
constraints:
  system_fatigue: "< 0.9"
goal_synthesis:
  min_priority: 0.5
""")

    @patch('sys.stdout', new_callable=StringIO)
    def test_single_cycle_execution(self, mock_stdout):
        """
        Tests that a single cycle of the DAO-Core runs without raising exceptions.
        It also checks if the output contains expected markers from each phase.
        """
        print("--- Running test_single_cycle_execution ---")

        try:
            # Instantiate and run the DAO Core
            dao_core = DaoCore()
            dao_core.run_single_cycle()

            # Get the output captured from stdout
            output = mock_stdout.getvalue()

            # --- Assertions to verify the flow ---

            # Check for initialization messages
            self.assertIn("Initializing Katana DAO-Core...", output)
            self.assertIn("DAO-Core Initialized.", output)

            # Check for the start of the cycle
            self.assertIn("STARTING DAO CYCLE", output)

            # 1. Observe Phase
            self.assertIn("--- 1. OBSERVE ---", output)
            self.assertIn("State Monitor Report:", output)

            # 2. Synthesize Goal Phase
            self.assertIn("--- 2. SYNTHESIZE GOAL ---", output)
            self.assertIn("Synthesized Goal:", output)
            # This checks the mock LLM's output for a healthy system
            self.assertIn("find_and_index_new_sources", output)

            # 3. Plan Phase
            self.assertIn("--- 3. PLAN ---", output)
            self.assertIn("Generated Plan:", output)
            # This checks the mock planner's output
            # self.assertIn("action: \"query_memory_weaver\"", output)

            # 4. Execute Phase
            self.assertIn("--- 4. EXECUTE ---", output)
            self.assertIn("EXECUTING PLAN", output)
            # self.assertIn("Step 1: query_memory_weaver", output)
            # self.assertIn("Step 4: process_and_index_results", output)
            self.assertIn("PLAN EXECUTION FINISHED", output)

            # Check for the end of the cycle
            self.assertIn("DAO CYCLE END", output)

            print("\n--- Test successfully verified all stages of the DAO cycle ---")

        except Exception as e:
            # If any exception occurs, the test fails
            self.fail(f"DAO Core cycle failed with an exception: {e}\nCaptured output:\n{mock_stdout.getvalue()}")

if __name__ == '__main__':
    unittest.main()
