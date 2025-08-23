import unittest
from unittest.mock import patch, MagicMock

from katana.psyche_profiler.profiler import PsycheProfiler

class TestPsycheProfiler(unittest.TestCase):

    def setUp(self):
        """Set up a mock Supabase client for the profiler tests."""
        self.mock_supabase_client = MagicMock()

        # Create separate mocks for each table
        self.mock_interactions_table = MagicMock()
        self.mock_archetype_table = MagicMock()

        # Configure the main client mock to return the correct table mock
        def table_side_effect(table_name):
            if table_name == 'oracle_interactions':
                return self.mock_interactions_table
            elif table_name == 'archetype_library':
                return self.mock_archetype_table
            return MagicMock()

        self.mock_supabase_client.table.side_effect = table_side_effect

    def test_run_profiling_full_pipeline(self):
        """
        Tests the full pipeline of the PsycheProfiler, ensuring placeholder methods are called correctly.
        """
        # --- Arrange ---
        # Configure the mock for a SUCCESSFUL fetch operation
        mock_fetch_response = MagicMock()
        mock_fetch_response.data = [
            {"user_id": "user_a", "question": "q1", "answer": "a1", "user_feedback": 5},
            {"user_id": "user_b", "question": "q2", "answer": "a2", "user_feedback": 1},
        ]
        mock_fetch_response.error = None # Explicitly set error to None for success
        self.mock_interactions_table.select.return_value.execute.return_value = mock_fetch_response

        # Configure the mock for a SUCCESSFUL insert operation
        self.mock_archetype_table.insert.return_value.execute.return_value = MagicMock(error=None)

        profiler = PsycheProfiler(self.mock_supabase_client)

        # --- Act ---
        profiler.run_profiling()

        # --- Assert ---
        # 1. Verify that the fetch was attempted on the correct table
        self.mock_interactions_table.select.assert_called_once()

        # 2. Verify that the save was attempted on the correct table
        self.mock_archetype_table.insert.assert_called_once()

        # 3. Inspect the data passed to the insert call
        insert_call_args = self.mock_archetype_table.insert.call_args
        self.assertIsNotNone(insert_call_args)

        inserted_data = insert_call_args[0][0]
        self.assertIsInstance(inserted_data, list)
        self.assertEqual(len(inserted_data), 2)

        utilitarian_archetype = inserted_data[0]
        self.assertEqual(utilitarian_archetype['name'], 'Archetype-Utilitarian-1')

    def test_run_profiling_no_data(self):
        """
        Tests that the pipeline gracefully exits if no data is fetched.
        """
        # --- Arrange ---
        # Configure the mock to return no data for this specific test
        mock_fetch_response = MagicMock()
        mock_fetch_response.data = []
        mock_fetch_response.error = None
        self.mock_interactions_table.select.return_value.execute.return_value = mock_fetch_response

        profiler = PsycheProfiler(self.mock_supabase_client)

        with patch.object(profiler, '_cluster_decisions') as mock_cluster:
            # --- Act ---
            profiler.run_profiling()

            # --- Assert ---
            # Verify that the pipeline stopped and did not attempt to cluster
            mock_cluster.assert_not_called()
            # Verify no attempt was made to save archetypes either
            self.mock_archetype_table.insert.assert_not_called()

if __name__ == "__main__":
    unittest.main()
