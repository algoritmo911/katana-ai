import os
import unittest
from unittest.mock import patch, MagicMock
import logging
import json

from katana.memory.core import MemoryCore

# Configure logger for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestMemoryCore(unittest.TestCase):

    def setUp(self):
        """Set up a mock Supabase client before each test."""
        # This patch ensures that the real 'create_client' is not called.
        self.patcher = patch('katana.memory.core.create_client')
        self.mock_create_client = self.patcher.start()
        self.mock_supabase_client = MagicMock()
        self.mock_create_client.return_value = self.mock_supabase_client

    def tearDown(self):
        """Stop the patcher after each test."""
        self.patcher.stop()

    @patch.dict(os.environ, {"SUPABASE_URL": "http://test.supabase.co", "SUPABASE_KEY": "test_key"})
    def test_init_success(self):
        """Test successful initialization of MemoryCore."""
        memory_core = MemoryCore()
        self.mock_create_client.assert_called_once_with("http://test.supabase.co", "test_key")
        self.assertEqual(memory_core.client, self.mock_supabase_client)

    @patch.dict(os.environ, {"SUPABASE_URL": "", "SUPABASE_KEY": ""})
    def test_init_failure_missing_credentials(self):
        """Test initialization failure when Supabase credentials are not set."""
        with self.assertLogs('katana.memory.core', level='WARNING') as cm:
            memory_core = MemoryCore()
            self.assertIsNone(memory_core.client)
            self.assertIn("SUPABASE_URL and/or SUPABASE_KEY environment variables are not set", cm.output[0])
        self.mock_create_client.assert_not_called()

    # --- Dialogue (command_logs) Tests ---

    @patch.dict(os.environ, {"SUPABASE_URL": "http://test.supabase.co", "SUPABASE_KEY": "test_key"})
    def test_add_dialogue_success(self):
        """Test successfully adding a dialogue log."""
        memory_core = MemoryCore()
        mock_response = MagicMock()
        mock_response.data = [{"id": 1, "user_id": "test_user"}]
        mock_response.error = None
        self.mock_supabase_client.table.return_value.insert.return_value.execute.return_value = mock_response

        result = memory_core.add_dialogue(
            user_id="test_user", command_name="test_cmd", input_data={},
            output_data={}, duration=0.1, success=True
        )
        self.assertEqual(result, [{"id": 1, "user_id": "test_user"}])
        self.mock_supabase_client.table.assert_called_with("command_logs")

    @patch.dict(os.environ, {"SUPABASE_URL": "http://test.supabase.co", "SUPABASE_KEY": "test_key"})
    def test_get_dialogue_success(self):
        """Test successfully getting a dialogue log."""
        memory_core = MemoryCore()
        mock_response = MagicMock()
        mock_response.data = [{"id": 1, "command_name": "test_cmd"}]
        mock_response.error = None
        self.mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        result = memory_core.get_dialogue(1)
        self.assertEqual(result, [{"id": 1, "command_name": "test_cmd"}])

    @patch.dict(os.environ, {"SUPABASE_URL": "http://test.supabase.co", "SUPABASE_KEY": "test_key"})
    def test_update_dialogue_success(self):
        """Test successfully updating a dialogue log."""
        memory_core = MemoryCore()
        mock_response = MagicMock()
        mock_response.data = [{"id": 1, "success": False}]
        mock_response.error = None
        self.mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response
        result = memory_core.update_dialogue(1, {"success": False})
        self.assertEqual(result, [{"id": 1, "success": False}])

    @patch.dict(os.environ, {"SUPABASE_URL": "http://test.supabase.co", "SUPABASE_KEY": "test_key"})
    def test_delete_dialogue_success(self):
        """Test successfully deleting a dialogue log."""
        memory_core = MemoryCore()
        mock_response = MagicMock()
        mock_response.data = [{"id": 1}]
        mock_response.error = None
        self.mock_supabase_client.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_response
        result = memory_core.delete_dialogue(1)
        self.assertEqual(result, [{"id": 1}])

    @patch.dict(os.environ, {"SUPABASE_URL": "http://test.supabase.co", "SUPABASE_KEY": "test_key"})
    def test_get_dialogue_history_success(self):
        """Test successfully getting dialogue history."""
        memory_core = MemoryCore()
        mock_response = MagicMock()
        mock_response.data = [{"id": 2}, {"id": 1}]
        mock_response.error = None
        self.mock_supabase_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_response
        result = memory_core.get_dialogue_history("test_user", limit=5)
        self.assertEqual(result, [{"id": 2}, {"id": 1}])

    # --- Fact (insights) Tests ---

    @patch.dict(os.environ, {"SUPABASE_URL": "http://test.supabase.co", "SUPABASE_KEY": "test_key"})
    def test_add_fact_success(self):
        """Test successfully adding a fact."""
        memory_core = MemoryCore()
        mock_response = MagicMock()
        mock_response.data = [{"id": 1, "content": "test fact"}]
        mock_response.error = None
        self.mock_supabase_client.table.return_value.insert.return_value.execute.return_value = mock_response
        result = memory_core.add_fact("test_user", "observation", "test fact")
        self.assertEqual(result, [{"id": 1, "content": "test fact"}])
        self.mock_supabase_client.table.assert_called_with("insights")

    @patch.dict(os.environ, {"SUPABASE_URL": "http://test.supabase.co", "SUPABASE_KEY": "test_key"})
    def test_get_fact_not_found(self):
        """Test getting a fact that does not exist."""
        memory_core = MemoryCore()
        mock_response = MagicMock()
        mock_response.data = []
        mock_response.error = None
        self.mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        with self.assertLogs('katana.memory.core', level='WARNING') as cm:
            result = memory_core.get_fact(999)
            self.assertIsNone(result)
            self.assertIn("get_fact returned no data and no error", cm.output[0])

    # --- Memory File (notes) Tests ---

    @patch.dict(os.environ, {"SUPABASE_URL": "http://test.supabase.co", "SUPABASE_KEY": "test_key"})
    def test_store_memory_file_string_content(self):
        memory_core = MemoryCore()
        mock_response = MagicMock()
        mock_response.data = [{"id": 1, "title": "Test Note"}]
        mock_response.error = None
        self.mock_supabase_client.table.return_value.insert.return_value.execute.return_value = mock_response
        result = memory_core.store_memory_file("Test Note", "This is the content.")
        self.assertEqual(result, [{"id": 1, "title": "Test Note"}])
        called_with_data = self.mock_supabase_client.table.return_value.insert.call_args[0][0]
        self.assertEqual(called_with_data['content'], "This is the content.")

    @patch.dict(os.environ, {"SUPABASE_URL": "http://test.supabase.co", "SUPABASE_KEY": "test_key"})
    def test_store_memory_file_dict_content(self):
        memory_core = MemoryCore()
        mock_response = MagicMock()
        mock_response.data = [{"id": 2, "title": "JSON Note"}]
        mock_response.error = None
        self.mock_supabase_client.table.return_value.insert.return_value.execute.return_value = mock_response
        dict_content = {"key": "value", "number": 123}
        result = memory_core.store_memory_file("JSON Note", dict_content)
        self.assertEqual(result, [{"id": 2, "title": "JSON Note"}])
        called_with_data = self.mock_supabase_client.table.return_value.insert.call_args[0][0]
        self.assertEqual(called_with_data['content'], json.dumps(dict_content))

    @patch.dict(os.environ, {"SUPABASE_URL": "http://test.supabase.co", "SUPABASE_KEY": "test_key"})
    def test_store_memory_file_serialization_error(self):
        memory_core = MemoryCore()
        non_serializable_content = object()
        with self.assertLogs('katana.memory.core', level='ERROR') as cm:
            result = memory_core.store_memory_file("Bad Note", non_serializable_content)
            self.assertIsNone(result)
            self.assertIn("Failed to serialize content for memory file 'Bad Note'", cm.output[0])

    # --- Error and Edge Case Tests ---

    @patch.dict(os.environ, {"SUPABASE_URL": "http://test.supabase.co", "SUPABASE_KEY": "test_key"})
    def test_supabase_error(self):
        """Test handling of a Supabase error response."""
        memory_core = MemoryCore()
        mock_response = MagicMock()
        mock_response.data = None
        mock_response.error = "Simulated database error"
        self.mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        with self.assertLogs('katana.memory.core', level='ERROR') as cm:
            result = memory_core.get_dialogue(1)
            self.assertIsNone(result)
            self.assertIn("Error during Supabase get_dialogue: Simulated database error", cm.output[0])

    @patch.dict(os.environ, {"SUPABASE_URL": "http://test.supabase.co", "SUPABASE_KEY": "test_key"})
    def test_unexpected_exception(self):
        """Test handling of an unexpected exception during a database call."""
        memory_core = MemoryCore()
        self.mock_supabase_client.table.return_value.insert.return_value.execute.side_effect = Exception("Network error")

        with self.assertLogs('katana.memory.core', level='ERROR') as cm:
            result = memory_core.add_dialogue("user", "cmd", {}, {}, 0.1, True)
            self.assertIsNone(result)
            self.assertIn("Unexpected error storing log: Network error", cm.output[0])

    @patch.dict(os.environ, {"SUPABASE_URL": "", "SUPABASE_KEY": ""})
    def test_operation_with_uninitialized_client(self):
        """Test that operations fail gracefully if the client is not initialized."""
        with self.assertLogs('katana.memory.core', level='ERROR') as cm:
            memory_core = MemoryCore()
            result = memory_core.add_dialogue("user", "cmd", {}, {}, 0.1, True)
            self.assertIsNone(result)
            self.assertIn("Supabase client not initialized. Cannot store log.", cm.output[0])

    @patch.dict(os.environ, {"SUPABASE_URL": "http://test.supabase.co", "SUPABASE_KEY": "test_key"})
    def test_add_dialogue_no_tags(self):
        """Test add_dialogue when tags are not provided."""
        memory_core = MemoryCore()
        mock_response = MagicMock()
        mock_response.data = [{"id": 1}]
        mock_response.error = None
        self.mock_supabase_client.table.return_value.insert.return_value.execute.return_value = mock_response
        memory_core.add_dialogue(
            user_id="test_user", command_name="test_cmd", input_data={},
            output_data={}, duration=0.1, success=True, tags=None
        )
        # Check that the inserted data has an empty list for tags
        called_with_data = self.mock_supabase_client.table.return_value.insert.call_args[0][0]
        self.assertEqual(called_with_data['tags'], [])

    @patch.dict(os.environ, {"SUPABASE_URL": "http://test.supabase.co", "SUPABASE_KEY": "test_key"})
    def test_store_memory_file_with_source(self):
        """Test store_memory_file with a source file."""
        memory_core = MemoryCore()
        mock_response = MagicMock()
        mock_response.data = [{"id": 1}]
        mock_response.error = None
        self.mock_supabase_client.table.return_value.insert.return_value.execute.return_value = mock_response
        memory_core.store_memory_file("Test", "content", source_file="test.txt")
        called_with_data = self.mock_supabase_client.table.return_value.insert.call_args[0][0]
        self.assertEqual(called_with_data['source_file'], "test.txt")

    @patch.dict(os.environ, {"SUPABASE_URL": "http://test.supabase.co", "SUPABASE_KEY": "test_key"})
    def test_get_facts_by_user_success(self):
        """Test successfully getting facts by user."""
        memory_core = MemoryCore()
        mock_response = MagicMock()
        mock_response.data = [{"id": 1, "user_id": "test_user"}]
        mock_response.error = None
        self.mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        result = memory_core.get_facts_by_user("test_user")
        self.assertEqual(result, [{"id": 1, "user_id": "test_user"}])

    @patch.dict(os.environ, {"SUPABASE_URL": "http://test.supabase.co", "SUPABASE_KEY": "test_key"})
    def test_update_fact_success(self):
        """Test successfully updating a fact."""
        memory_core = MemoryCore()
        mock_response = MagicMock()
        mock_response.data = [{"id": 1, "content": "updated"}]
        mock_response.error = None
        self.mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response
        result = memory_core.update_fact(1, {"content": "updated"})
        self.assertEqual(result, [{"id": 1, "content": "updated"}])

    @patch.dict(os.environ, {"SUPABASE_URL": "http://test.supabase.co", "SUPABASE_KEY": "test_key"})
    def test_delete_fact_success(self):
        """Test successfully deleting a fact."""
        memory_core = MemoryCore()
        mock_response = MagicMock()
        mock_response.data = [{"id": 1}]
        mock_response.error = None
        self.mock_supabase_client.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_response
        result = memory_core.delete_fact(1)
        self.assertEqual(result, [{"id": 1}])

    def test_all_methods_uninitialized(self):
        """Test that all methods handle an uninitialized client."""
        with self.assertLogs('katana.memory.core', level='ERROR') as cm:
            memory_core = MemoryCore()
            # Set client to None to be sure
            memory_core.client = None
            self.assertIsNone(memory_core.get_dialogue(1))
            self.assertIsNone(memory_core.update_dialogue(1, {}))
            self.assertIsNone(memory_core.delete_dialogue(1))
            self.assertIsNone(memory_core.add_fact("user", "type", "content"))
            self.assertIsNone(memory_core.get_fact(1))
            self.assertIsNone(memory_core.get_facts_by_user("user"))
            self.assertIsNone(memory_core.update_fact(1, {}))
            self.assertIsNone(memory_core.delete_fact(1))
            self.assertIsNone(memory_core.get_dialogue_history("user"))
            self.assertIsNone(memory_core.store_memory_file("title", "content"))


    def test_all_methods_exceptions(self):
        """Test that all methods handle exceptions during Supabase calls."""
        methods_to_test = {
            "get_dialogue": (1,),
            "update_dialogue": (1, {}),
            "delete_dialogue": (1,),
            "add_fact": ("user", "type", "content"),
            "get_fact": (1,),
            "get_facts_by_user": ("user",),
            "update_fact": (1, {}),
            "delete_fact": (1,),
            "get_dialogue_history": ("user",),
            "store_memory_file": ("title", "content"),
        }

        for method_name, args in methods_to_test.items():
            with self.subTest(method=method_name):
                with patch.dict(os.environ, {"SUPABASE_URL": "http://test.supabase.co", "SUPABASE_KEY": "test_key"}):
                    memory_core = MemoryCore()
                    # Mock the chain of calls to raise an exception at the end
                    self.mock_supabase_client.table.return_value.insert.return_value.execute.side_effect = Exception("DB Error")
                    self.mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception("DB Error")
                    self.mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.side_effect = Exception("DB Error")
                    self.mock_supabase_client.table.return_value.delete.return_value.eq.return_value.execute.side_effect = Exception("DB Error")
                    self.mock_supabase_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.side_effect = Exception("DB Error")


                    with self.assertLogs('katana.memory.core', level='ERROR'):
                        result = getattr(memory_core, method_name)(*args)
                        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
