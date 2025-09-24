import os
import json
import logging
from datetime import datetime
from supabase import create_client, Client
from typing import List, Dict, Any, Optional

# Initialize logger
logger = logging.getLogger(__name__)

# Get Supabase credentials from environment variables
SUPABASE_URL: Optional[str] = os.getenv("SUPABASE_URL")
SUPABASE_KEY: Optional[str] = os.getenv("SUPABASE_KEY")

class SupabaseMemoryClient:
    def __init__(self):
        if SUPABASE_URL and SUPABASE_KEY:
            self.client: Optional[Client] = create_client(SUPABASE_URL, SUPABASE_KEY)
            logger.info("Supabase client initialized successfully.")
        else:
            self.client = None
            logger.warning(
                "SUPABASE_URL and/or SUPABASE_KEY environment variables are not set. "
                "SupabaseMemoryClient will not be functional."
            )

    def _handle_response(self, response, operation_name: str):
        """Helper function to handle Supabase response and errors."""
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error during Supabase {operation_name}: {response.error}")
            return None
        if hasattr(response, 'data') and response.data:
            logger.debug(f"Supabase {operation_name} successful. Data: {response.data}")
            return response.data
        logger.warning(f"Supabase {operation_name} returned no data and no error.")
        return None

    def store_log(
        self,
        user_id: str,
        command_name: str,
        input_data: Any,
        output_data: Any,
        duration: float,
        success: bool,
        tags: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        if not self.client:
            logger.error("Supabase client not initialized. Cannot store log.")
            return None
        if tags is None:
            tags = []

        log_entry = {
            "user_id": user_id,
            "command_name": command_name,
            "input_data": json.dumps(input_data) if input_data is not None else None,
            "output_data": json.dumps(output_data) if output_data is not None else None,
            "duration": duration,
            "success": success,
            "tags": tags,
            "timestamp": datetime.utcnow().isoformat() + "+00:00",  # ISO 8601 with UTC timezone
        }
        try:
            response = self.client.table("command_logs").insert(log_entry).execute()
            return self._handle_response(response, "store_log")
        except Exception as e:
            logger.error(f"Unexpected error storing log: {e}", exc_info=True)
            return None

    def store_insight(
        self, user_id: str, insight_type: str, content: str
    ) -> Optional[Dict[str, Any]]:
        if not self.client:
            logger.error("Supabase client not initialized. Cannot store insight.")
            return None

        insight_entry = {
            "user_id": user_id,
            "type": insight_type,
            "content": content,
            "timestamp": datetime.utcnow().isoformat() + "+00:00",
        }
        try:
            response = self.client.table("insights").insert(insight_entry).execute()
            return self._handle_response(response, "store_insight")
        except Exception as e:
            logger.error(f"Unexpected error storing insight: {e}", exc_info=True)
            return None

    def fetch_recent_logs(
        self, user_id: str, limit: int = 10
    ) -> Optional[List[Dict[str, Any]]]:
        if not self.client:
            logger.error("Supabase client not initialized. Cannot fetch logs.")
            return None
        try:
            # Assuming 'timestamp' is the column to order by, and it's stored in a way Supabase can sort descending.
            # Supabase Python client uses `desc=True` in the `order` method.
            response = (
                self.client.table("command_logs")
                .select("*")
                .eq("user_id", user_id)
                .order("timestamp", desc=True)
                .limit(limit)
                .execute()
            )
            return self._handle_response(response, "fetch_recent_logs")
        except Exception as e:
            logger.error(f"Unexpected error fetching recent logs: {e}", exc_info=True)
            return None

    def store_memory_file(
        self, title: str, content: Any, tags: Optional[List[str]] = None, source_file: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        if not self.client:
            logger.error("Supabase client not initialized. Cannot store memory file.")
            return None
        if tags is None:
            tags = []

        # If content is not a string, attempt to dump it as JSON.
        # This is useful if YAML content is parsed into dicts/lists before storing.
        processed_content = content
        if not isinstance(content, str):
            try:
                processed_content = json.dumps(content)
            except TypeError as e:
                logger.error(f"Failed to serialize content for memory file '{title}': {e}", exc_info=True)
                return None

        memory_entry = {
            "title": title,
            "content": processed_content,
            "tags": tags,
            "timestamp": datetime.utcnow().isoformat() + "+00:00",
        }
        if source_file:
            memory_entry["source_file"] = source_file

        try:
            response = self.client.table("notes").insert(memory_entry).execute()
            return self._handle_response(response, "store_memory_file")
        except Exception as e:
            logger.error(f"Unexpected error storing memory file: {e}", exc_info=True)
            return None

    # -----------------------------------------------------------------
    # Coder CRUD operations
    # -----------------------------------------------------------------
    def add_coder(self, username: str) -> Optional[Dict[str, Any]]:
        """Adds a new coder to the 'coders' table."""
        if not self.client:
            logger.error("Supabase client not initialized. Cannot add coder.")
            return None
        try:
            response = self.client.table("coders").insert({"username": username}).execute()
            return self._handle_response(response, "add_coder")
        except Exception as e:
            logger.error(f"Unexpected error adding coder: {e}", exc_info=True)
            return None

    def get_coder_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Retrieves a coder by their username."""
        if not self.client:
            logger.error("Supabase client not initialized. Cannot get coder.")
            return None
        try:
            response = self.client.table("coders").select("*").eq("username", username).execute()
            return self._handle_response(response, "get_coder_by_username")
        except Exception as e:
            logger.error(f"Unexpected error getting coder by username: {e}", exc_info=True)
            return None

    def get_coder_by_id(self, coder_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a coder by their ID."""
        if not self.client:
            logger.error("Supabase client not initialized. Cannot get coder.")
            return None
        try:
            response = self.client.table("coders").select("*").eq("id", coder_id).execute()
            return self._handle_response(response, "get_coder_by_id")
        except Exception as e:
            logger.error(f"Unexpected error getting coder by id: {e}", exc_info=True)
            return None

    def get_all_coders(self) -> Optional[List[Dict[str, Any]]]:
        """Retrieves all coders."""
        if not self.client:
            logger.error("Supabase client not initialized. Cannot get all coders.")
            return None
        try:
            response = self.client.table("coders").select("*").execute()
            return self._handle_response(response, "get_all_coders")
        except Exception as e:
            logger.error(f"Unexpected error getting all coders: {e}", exc_info=True)
            return None

    def update_coder(self, coder_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Updates a coder's information."""
        if not self.client:
            logger.error("Supabase client not initialized. Cannot update coder.")
            return None
        try:
            response = self.client.table("coders").update(updates).eq("id", coder_id).execute()
            return self._handle_response(response, "update_coder")
        except Exception as e:
            logger.error(f"Unexpected error updating coder: {e}", exc_info=True)
            return None

    def delete_coder(self, coder_id: str) -> Optional[Dict[str, Any]]:
        """Deletes a coder by their ID."""
        if not self.client:
            logger.error("Supabase client not initialized. Cannot delete coder.")
            return None
        try:
            response = self.client.table("coders").delete().eq("id", coder_id).execute()
            return self._handle_response(response, "delete_coder")
        except Exception as e:
            logger.error(f"Unexpected error deleting coder: {e}", exc_info=True)
            return None

    # -----------------------------------------------------------------
    # Task CRUD operations
    # -----------------------------------------------------------------
    def add_task(
        self, title: str, description: Optional[str] = None, coder_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Adds a new task to the 'tasks' table."""
        if not self.client:
            logger.error("Supabase client not initialized. Cannot add task.")
            return None
        try:
            task = {"title": title, "description": description, "coder_id": coder_id}
            response = self.client.table("tasks").insert(task).execute()
            return self._handle_response(response, "add_task")
        except Exception as e:
            logger.error(f"Unexpected error adding task: {e}", exc_info=True)
            return None

    def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a task by its ID."""
        if not self.client:
            logger.error("Supabase client not initialized. Cannot get task.")
            return None
        try:
            response = self.client.table("tasks").select("*").eq("id", task_id).execute()
            return self._handle_response(response, "get_task_by_id")
        except Exception as e:
            logger.error(f"Unexpected error getting task by id: {e}", exc_info=True)
            return None

    def get_all_tasks(self) -> Optional[List[Dict[str, Any]]]:
        """Retrieves all tasks."""
        if not self.client:
            logger.error("Supabase client not initialized. Cannot get all tasks.")
            return None
        try:
            response = self.client.table("tasks").select("*").execute()
            return self._handle_response(response, "get_all_tasks")
        except Exception as e:
            logger.error(f"Unexpected error getting all tasks: {e}", exc_info=True)
            return None

    def get_tasks_by_coder(self, coder_id: str) -> Optional[List[Dict[str, Any]]]:
        """Retrieves all tasks assigned to a specific coder."""
        if not self.client:
            logger.error("Supabase client not initialized. Cannot get tasks.")
            return None
        try:
            response = self.client.table("tasks").select("*").eq("coder_id", coder_id).execute()
            return self._handle_response(response, "get_tasks_by_coder")
        except Exception as e:
            logger.error(f"Unexpected error getting tasks by coder: {e}", exc_info=True)
            return None

    def update_task(self, task_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Updates a task's information."""
        if not self.client:
            logger.error("Supabase client not initialized. Cannot update task.")
            return None
        try:
            response = self.client.table("tasks").update(updates).eq("id", task_id).execute()
            return self._handle_response(response, "update_task")
        except Exception as e:
            logger.error(f"Unexpected error updating task: {e}", exc_info=True)
            return None

    def delete_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Deletes a task by its ID."""
        if not self.client:
            logger.error("Supabase client not initialized. Cannot delete task.")
            return None
        try:
            response = self.client.table("tasks").delete().eq("id", task_id).execute()
            return self._handle_response(response, "delete_task")
        except Exception as e:
            logger.error(f"Unexpected error deleting task: {e}", exc_info=True)
            return None

    def assign_task_to_coder(self, task_id: str, coder_id: str) -> Optional[Dict[str, Any]]:
        """Assigns a task to a coder."""
        return self.update_task(task_id, {"coder_id": coder_id})


# Example usage (for testing purposes, remove later)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Ensure SUPABASE_URL and SUPABASE_KEY are set in your environment
    # For example, create a .env file and load it with python-dotenv
    # from dotenv import load_dotenv
    # load_dotenv()

    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
        logger.error("Please set SUPABASE_URL and SUPABASE_KEY environment variables to run this example.")
    else:
        client = SupabaseMemoryClient()
        if client.client:  # Check if client was initialized
            logger.info("Supabase client created. Attempting operations...")

            # Test store_log
            log_data = client.store_log(
                user_id="test_user_123",
                command_name="greet",
                input_data={"name": "Jules"},
                output_data={"message": "Hello Jules!"},
                duration=0.5,
                success=True,
                tags=["test", "greeting"],
            )
            if log_data:
                logger.info(f"Stored log: {log_data}")

            # Test store_insight
            insight_data = client.store_insight(
                user_id="test_user_123",
                insight_type="test_observation",
                content="This is a test insight from example usage.",
            )
            if insight_data:
                logger.info(f"Stored insight: {insight_data}")

            # Test fetch_recent_logs
            recent_logs = client.fetch_recent_logs(user_id="test_user_123", limit=5)
            if recent_logs:
                logger.info(f"Fetched recent logs: {recent_logs}")
            else:
                logger.warning("No recent logs fetched or an error occurred.")

            # Test store_memory_file
            memory_content = {"data": "This is a test memory item.", "version": 1}
            file_data = client.store_memory_file(
                title="Test Memory Item",
                content=memory_content, # Stored as JSON string
                tags=["test", "yaml_like"],
                source_file="example_script.py"
            )
            if file_data:
                logger.info(f"Stored memory file: {file_data}")
        else:
            logger.error("Supabase client could not be initialized. Operations skipped.")
