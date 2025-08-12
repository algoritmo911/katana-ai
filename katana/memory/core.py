import os
import json
import logging
from datetime import datetime, timezone
from supabase import create_client, Client
from typing import List, Dict, Any, Optional

from katana.services.vectorization import VectorizationService

# Initialize logger
logger = logging.getLogger(__name__)

class MemoryCore:
    """
    A class to handle all interactions with the Supabase database.
    This class provides a complete CRUD interface for all memory-related tables.
    """
    def __init__(self):
        """
        Initializes the MemoryCore client.
        It reads the Supabase URL and Key from the environment variables.
        If they are not set, the client will not be functional.
        """
        supabase_url: Optional[str] = os.getenv("SUPABASE_URL")
        supabase_key: Optional[str] = os.getenv("SUPABASE_KEY")
        if supabase_url and supabase_key:
            self.client: Optional[Client] = create_client(supabase_url, supabase_key)
            logger.info("Supabase client initialized successfully.")
        else:
            self.client = None
            logger.warning(
                "SUPABASE_URL and/or SUPABASE_KEY environment variables are not set. "
                "MemoryCore will not be functional."
            )
        self.vectorization_service = VectorizationService()

    def _handle_response(self, response, operation_name: str):
        """
        Helper function to handle Supabase response and errors.

        Args:
            response: The response object from the Supabase client.
            operation_name: The name of the operation being performed.

        Returns:
            The data from the response if successful, otherwise None.
        """
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error during Supabase {operation_name}: {response.error}")
            return None
        if hasattr(response, 'data') and response.data:
            logger.debug(f"Supabase {operation_name} successful. Data: {response.data}")
            return response.data
        logger.warning(f"Supabase {operation_name} returned no data and no error.")
        return None

    def add_dialogue(
        self,
        user_id: str,
        command_name: str,
        input_data: Any,
        output_data: Any,
        duration: float,
        success: bool,
        tags: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Adds a new dialogue entry to the command_logs table.

        Args:
            user_id: The ID of the user.
            command_name: The name of the command that was executed.
            input_data: The input data for the command.
            output_data: The output data from the command.
            duration: The duration of the command execution in seconds.
            success: Whether the command was successful or not.
            tags: A list of tags to associate with the dialogue.

        Returns:
            The newly created dialogue entry, or None if an error occurred.
        """
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            response = self.client.table("command_logs").insert(log_entry).execute()
            dialogue_data = self._handle_response(response, "add_dialogue")
            if dialogue_data and dialogue_data[0].get("id"):
                dialogue_id = dialogue_data[0]["id"]
                # Combine input and output for vectorization
                text_to_vectorize = f"Input: {log_entry['input_data']} Output: {log_entry['output_data']}"
                embedding = self.vectorization_service.vectorize(text_to_vectorize)
                if embedding:
                    self.store_embedding(dialogue_id, text_to_vectorize, embedding)
                else:
                    logger.warning(f"Could not generate embedding for dialogue_id: {dialogue_id}")
            return dialogue_data
        except Exception as e:
            logger.error(f"Unexpected error storing log: {e}", exc_info=True)
            return None

    def get_dialogue(self, log_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieves a specific dialogue entry by its ID.

        Args:
            log_id: The ID of the dialogue entry to retrieve.

        Returns:
            The dialogue entry, or None if not found or an error occurred.
        """
        if not self.client:
            logger.error("Supabase client not initialized. Cannot get dialogue.")
            return None
        try:
            response = self.client.table("command_logs").select("*").eq("id", log_id).execute()
            return self._handle_response(response, "get_dialogue")
        except Exception as e:
            logger.error(f"Unexpected error getting dialogue: {e}", exc_info=True)
            return None

    def update_dialogue(self, log_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Updates an existing dialogue entry.

        Args:
            log_id: The ID of the dialogue entry to update.
            updates: A dictionary of fields to update.

        Returns:
            The updated dialogue entry, or None if an error occurred.
        """
        if not self.client:
            logger.error("Supabase client not initialized. Cannot update dialogue.")
            return None
        try:
            response = self.client.table("command_logs").update(updates).eq("id", log_id).execute()
            return self._handle_response(response, "update_dialogue")
        except Exception as e:
            logger.error(f"Unexpected error updating dialogue: {e}", exc_info=True)
            return None

    def delete_dialogue(self, log_id: int) -> Optional[Dict[str, Any]]:
        """
        Deletes a dialogue entry.

        Args:
            log_id: The ID of the dialogue entry to delete.

        Returns:
            The deleted dialogue entry, or None if an error occurred.
        """
        if not self.client:
            logger.error("Supabase client not initialized. Cannot delete dialogue.")
            return None
        try:
            response = self.client.table("command_logs").delete().eq("id", log_id).execute()
            return self._handle_response(response, "delete_dialogue")
        except Exception as e:
            logger.error(f"Unexpected error deleting dialogue: {e}", exc_info=True)
            return None

    def add_fact(
        self, user_id: str, fact_type: str, content: str
    ) -> Optional[Dict[str, Any]]:
        """
        Adds a new fact to the insights table.

        Args:
            user_id: The ID of the user.
            fact_type: The type of the fact (e.g., 'observation', 'suggestion').
            content: The content of the fact.

        Returns:
            The newly created fact, or None if an error occurred.
        """
        if not self.client:
            logger.error("Supabase client not initialized. Cannot store insight.")
            return None

        insight_entry = {
            "user_id": user_id,
            "type": fact_type,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            response = self.client.table("insights").insert(insight_entry).execute()
            return self._handle_response(response, "add_fact")
        except Exception as e:
            logger.error(f"Unexpected error storing insight: {e}", exc_info=True)
            return None

    def get_fact(self, fact_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieves a specific fact by its ID.

        Args:
            fact_id: The ID of the fact to retrieve.

        Returns:
            The fact, or None if not found or an error occurred.
        """
        if not self.client:
            logger.error("Supabase client not initialized. Cannot get fact.")
            return None
        try:
            response = self.client.table("insights").select("*").eq("id", fact_id).execute()
            return self._handle_response(response, "get_fact")
        except Exception as e:
            logger.error(f"Unexpected error getting fact: {e}", exc_info=True)
            return None

    def get_facts_by_user(self, user_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieves all facts for a given user.

        Args:
            user_id: The ID of the user.

        Returns:
            A list of facts, or None if an error occurred.
        """
        if not self.client:
            logger.error("Supabase client not initialized. Cannot get facts.")
            return None
        try:
            response = self.client.table("insights").select("*").eq("user_id", user_id).execute()
            return self._handle_response(response, "get_facts_by_user")
        except Exception as e:
            logger.error(f"Unexpected error getting facts: {e}", exc_info=True)
            return None

    def update_fact(self, fact_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Updates an existing fact.

        Args:
            fact_id: The ID of the fact to update.
            updates: A dictionary of fields to update.

        Returns:
            The updated fact, or None if an error occurred.
        """
        if not self.client:
            logger.error("Supabase client not initialized. Cannot update fact.")
            return None
        try:
            response = self.client.table("insights").update(updates).eq("id", fact_id).execute()
            return self._handle_response(response, "update_fact")
        except Exception as e:
            logger.error(f"Unexpected error updating fact: {e}", exc_info=True)
            return None

    def delete_fact(self, fact_id: int) -> Optional[Dict[str, Any]]:
        """
        Deletes a fact.

        Args:
            fact_id: The ID of the fact to delete.

        Returns:
            The deleted fact, or None if an error occurred.
        """
        if not self.client:
            logger.error("Supabase client not initialized. Cannot delete fact.")
            return None
        try:
            response = self.client.table("insights").delete().eq("id", fact_id).execute()
            return self._handle_response(response, "delete_fact")
        except Exception as e:
            logger.error(f"Unexpected error deleting fact: {e}", exc_info=True)
            return None

    def store_embedding(
        self, dialogue_id: int, content: str, embedding: List[float]
    ) -> Optional[Dict[str, Any]]:
        """
        Stores a vector embedding in the vector_store table.

        Args:
            dialogue_id: The ID of the dialogue entry this embedding belongs to.
            content: The original text content that was vectorized.
            embedding: The vector embedding.

        Returns:
            The newly created embedding entry, or None if an error occurred.
        """
        if not self.client:
            logger.error("Supabase client not initialized. Cannot store embedding.")
            return None

        embedding_entry = {
            "dialogue_id": dialogue_id,
            "content": content,
            "embedding": embedding,
        }
        try:
            response = self.client.table("vector_store").insert(embedding_entry).execute()
            return self._handle_response(response, "store_embedding")
        except Exception as e:
            logger.error(f"Unexpected error storing embedding: {e}", exc_info=True)
            return None

    def get_dialogue_history(
        self, user_id: str, limit: int = 10
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieves the recent dialogue history for a user.

        Args:
            user_id: The ID of the user.
            limit: The maximum number of dialogue entries to retrieve.

        Returns:
            A list of dialogue entries, or None if an error occurred.
        """
        if not self.client:
            logger.error("Supabase client not initialized. Cannot fetch logs.")
            return None
        try:
            response = (
                self.client.table("command_logs")
                .select("*")
                .eq("user_id", user_id)
                .order("timestamp", desc=True)
                .limit(limit)
                .execute()
            )
            return self._handle_response(response, "get_dialogue_history")
        except Exception as e:
            logger.error(f"Unexpected error fetching recent logs: {e}", exc_info=True)
            return None

    def store_memory_file(
        self, title: str, content: Any, tags: Optional[List[str]] = None, source_file: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Stores a memory file in the notes table.
        The content can be a string or a dictionary that will be serialized to JSON.

        Args:
            title: The title of the memory file.
            content: The content of the memory file.
            tags: A list of tags to associate with the memory file.
            source_file: The path to the original file if synced from local YAML.

        Returns:
            The newly created memory file, or None if an error occurred.
        """
        if not self.client:
            logger.error("Supabase client not initialized. Cannot store memory file.")
            return None
        if tags is None:
            tags = []

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
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if source_file:
            memory_entry["source_file"] = source_file

        try:
            response = self.client.table("notes").insert(memory_entry).execute()
            return self._handle_response(response, "store_memory_file")
        except Exception as e:
            logger.error(f"Unexpected error storing memory file: {e}", exc_info=True)
            return None
