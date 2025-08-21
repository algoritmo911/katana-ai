import unittest
import time
from unittest.mock import MagicMock, patch

from katana.memory.core import MemoryCore

class TestMemoryFabricIntegration(unittest.TestCase):

    def setUp(self):
        """Set up the test environment before each test."""
        # Patch os.getenv to simulate having credentials
        self.getenv_patcher = patch('os.getenv', side_effect=lambda key: {
            "SUPABASE_URL": "http://mock.supabase.co",
            "SUPABASE_KEY": "mock_key",
            "OPENAI_API_KEY": "mock_openai_key" # Add this to avoid vectorization warnings
        }.get(key))
        self.mock_getenv = self.getenv_patcher.start()

        # We patch the create_client function to avoid real DB connections
        # and to be able to inject a mock client.
        self.create_client_patcher = patch('katana.memory.core.create_client')
        self.mock_create_client = self.create_client_patcher.start()

        # This mock will be returned by create_client
        self.mock_supabase_client = MagicMock()
        self.mock_create_client.return_value = self.mock_supabase_client

        # Create separate mocks for each table we interact with
        self.mock_nodes_table = MagicMock()
        self.mock_edges_table = MagicMock()
        self.mock_logs_table = MagicMock()
        self.mock_vector_store_table = MagicMock()

        # Configure the main client mock to return the correct table mock based on the name
        def table_side_effect(table_name):
            if table_name == 'nodes':
                return self.mock_nodes_table
            elif table_name == 'edges':
                return self.mock_edges_table
            elif table_name == 'command_logs':
                return self.mock_logs_table
            elif table_name == 'vector_store':
                return self.mock_vector_store_table
            # Return a default mock for any other table calls
            return MagicMock()

        self.mock_supabase_client.table.side_effect = table_side_effect

        # Mock the response from the 'insert' operation to simulate a successful DB insertion.
        # This response will be shared across the table mocks.
        mock_execute_response = MagicMock()
        mock_execute_response.data = [{'id': 'mock-node-id-12345', 'attributes': {}}]
        mock_execute_response.error = None

        # Configure the chain of mocks for EACH table mock
        self.mock_nodes_table.insert.return_value.execute.return_value = mock_execute_response
        self.mock_edges_table.insert.return_value.execute.return_value = mock_execute_response
        self.mock_logs_table.insert.return_value.execute.return_value = mock_execute_response
        self.mock_vector_store_table.insert.return_value.execute.return_value = mock_execute_response

        # Now, instantiate MemoryCore. It will be initialized with our mock client.
        self.memory_core = MemoryCore()

    def tearDown(self):
        """Clean up after each test."""
        self.create_client_patcher.stop()
        self.getenv_patcher.stop()

    def test_add_dialogue_triggers_full_pipeline(self):
        """
        Tests the end-to-end flow from adding a dialogue to building the graph.
        """
        # --- Arrange ---
        user_id = "test_user_123"
        command_name = "!greet"
        test_dialogue = {
            "user_id": user_id,
            "command_name": command_name,
            "input_data": {"command_string": "!greet"},
            "output_data": {"response": "Hello from KatanaBot!"},
            "duration": 0.5,
            "success": True,
            "tags": ["greeting"]
        }

        # --- Act ---
        self.memory_core.add_dialogue(**test_dialogue)

        # --- Assert ---
        # 1. Verify that the command_logs table was written to
        self.mock_logs_table.insert.assert_called_once()

        # 2. Verify that nodes were created in the graph
        nodes_insert_calls = self.mock_nodes_table.insert.call_args_list
        self.assertEqual(len(nodes_insert_calls), 2, "Expected two nodes to be created (Event and Author)")

        # 3. Verify that edges were created in the graph
        self.mock_edges_table.insert.assert_called_once()

        # 4. Inspect the calls to the 'nodes' table more closely
        # Check the MemoryEvent node
        event_node_call = nodes_insert_calls[0]
        event_node_data = event_node_call[0][0] # The data passed to insert()
        self.assertEqual(event_node_data['node_type'], 'MemoryEvent')
        self.assertIn('chronos_id', event_node_data)
        self.assertIsNotNone(event_node_data['chronos_id'])
        self.assertEqual(event_node_data['attributes']['command_name'], command_name)

        # Check the Author node
        author_node_call = nodes_insert_calls[1]
        author_node_data = author_node_call[0][0]
        self.assertEqual(author_node_data['node_type'], 'Author')
        self.assertEqual(author_node_data['attributes']['user_id'], user_id)

        # 5. Inspect the call to the 'edges' table
        edges_insert_call = self.mock_edges_table.insert.call_args
        self.assertIsNotNone(edges_insert_call, "Expected an edge to be created")
        edge_data = edges_insert_call[0][0]
        self.assertEqual(edge_data['edge_type'], 'authored')
        # We can't know the exact IDs since they are mocked, but we can check they exist
        self.assertIn('source_node_id', edge_data)
        self.assertIn('target_node_id', edge_data)

if __name__ == "__main__":
    unittest.main()
