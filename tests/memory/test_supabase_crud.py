import os
import logging
import unittest
from dotenv import load_dotenv
from katana.memory.supabase_client import SupabaseMemoryClient

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestSupabaseCrud(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up the Supabase client once for all tests."""
        cls.client = SupabaseMemoryClient()
        if not cls.client.client:
            raise unittest.SkipTest("Supabase client not initialized. Skipping tests.")
        logger.info("Supabase client initialized for testing.")

    def test_coder_crud_operations(self):
        """Test CRUD operations for the 'coders' table."""
        # 1. Add a new coder
        username = "test_coder_123"
        new_coder = self.client.add_coder(username)
        self.assertIsNotNone(new_coder)
        self.assertEqual(new_coder[0]['username'], username)
        coder_id = new_coder[0]['id']
        logger.info(f"Successfully added coder with ID: {coder_id}")

        # 2. Get the coder by ID
        coder_by_id = self.client.get_coder_by_id(coder_id)
        self.assertIsNotNone(coder_by_id)
        self.assertEqual(coder_by_id[0]['username'], username)

        # 3. Get the coder by username
        coder_by_username = self.client.get_coder_by_username(username)
        self.assertIsNotNone(coder_by_username)
        self.assertEqual(coder_by_username[0]['id'], coder_id)

        # 4. Update the coder
        updated_username = "updated_coder_456"
        updated_coder = self.client.update_coder(coder_id, {"username": updated_username})
        self.assertIsNotNone(updated_coder)
        self.assertEqual(updated_coder[0]['username'], updated_username)
        logger.info(f"Successfully updated coder {coder_id}")

        # 5. Delete the coder
        deleted_coder = self.client.delete_coder(coder_id)
        self.assertIsNotNone(deleted_coder)
        logger.info(f"Successfully deleted coder {coder_id}")

        # Verify deletion
        coder_after_delete = self.client.get_coder_by_id(coder_id)
        self.assertEqual(len(coder_after_delete), 0)

    def test_task_crud_operations(self):
        """Test CRUD operations for the 'tasks' table."""
        # Setup: Ensure a coder exists to assign tasks to
        coder_username = "task_coder_789"
        coder = self.client.add_coder(coder_username)
        self.assertIsNotNone(coder)
        coder_id = coder[0]['id']
        logger.info(f"Setup: Created coder {coder_id} for task tests.")

        # 1. Add a new task
        task_title = "Test Task"
        task_description = "This is a test task description."
        new_task = self.client.add_task(task_title, task_description, coder_id)
        self.assertIsNotNone(new_task)
        self.assertEqual(new_task[0]['title'], task_title)
        task_id = new_task[0]['id']
        logger.info(f"Successfully added task with ID: {task_id}")

        # 2. Get the task by ID
        task_by_id = self.client.get_task_by_id(task_id)
        self.assertIsNotNone(task_by_id)
        self.assertEqual(task_by_id[0]['title'], task_title)

        # 3. Update the task
        updated_title = "Updated Test Task"
        updated_task = self.client.update_task(task_id, {"title": updated_title, "status": "in_progress"})
        self.assertIsNotNone(updated_task)
        self.assertEqual(updated_task[0]['title'], updated_title)
        self.assertEqual(updated_task[0]['status'], "in_progress")
        logger.info(f"Successfully updated task {task_id}")

        # 4. Get tasks by coder
        tasks_for_coder = self.client.get_tasks_by_coder(coder_id)
        self.assertIsNotNone(tasks_for_coder)
        self.assertTrue(any(task['id'] == task_id for task in tasks_for_coder))

        # 5. Delete the task
        deleted_task = self.client.delete_task(task_id)
        self.assertIsNotNone(deleted_task)
        logger.info(f"Successfully deleted task {task_id}")

        # Verify deletion
        task_after_delete = self.client.get_task_by_id(task_id)
        self.assertEqual(len(task_after_delete), 0)

        # Teardown: Clean up the coder
        self.client.delete_coder(coder_id)
        logger.info(f"Teardown: Deleted coder {coder_id}")

if __name__ == "__main__":
    # Note: Running this test file directly will execute tests against the configured Supabase instance.
    # Make sure your .env file is correctly set up with SUPABASE_URL and SUPABASE_KEY.
    # These tests are destructive and will add and remove data from your tables.
    unittest.main()
