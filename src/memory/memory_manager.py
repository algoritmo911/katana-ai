import redis
import json
import os
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

class MemoryManager:
    """
    Manages short-term memory for chat histories using Redis.
    """
    DEFAULT_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days

    def __init__(self,
                 host: str = 'localhost',
                 port: int = 6379,
                 db: int = 0,
                 password: Optional[str] = None,
                 chat_history_ttl_seconds: Optional[int] = None):
        """
        Initializes the MemoryManager with Redis connection parameters.

        Args:
            host: Redis host.
            port: Redis port.
            db: Redis database number.
            password: Redis password.
            chat_history_ttl_seconds: TTL for chat history keys in seconds.
                                      Defaults to DEFAULT_TTL_SECONDS if None.
        """
        try:
            self.redis_client = redis.Redis(host=host, port=port, db=db, password=password, decode_responses=False)
            # Check connection
            self.redis_client.ping()
            logger.info(f"Successfully connected to Redis at {host}:{port}/{db}")
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Failed to connect to Redis at {host}:{port}/{db}: {e}", exc_info=True)
            # In a real application, you might want to raise this or have a fallback.
            # For now, we'll let operations fail if the client is not available.
            # Or, set self.redis_client to None and check in each method.
            self.redis_client = None # Indicate connection failure

        self.ttl_seconds = chat_history_ttl_seconds if chat_history_ttl_seconds is not None else self.DEFAULT_TTL_SECONDS
        if self.ttl_seconds <= 0:
            logger.warning(f"Chat history TTL is {self.ttl_seconds} seconds. Disabling TTL.")
            self.ttl_seconds = None # None means no TTL for redis client

    def _get_chat_key(self, chat_id: str) -> str:
        """Generates the Redis key for a given chat_id."""
        return f"chat_history:{chat_id}"

    def get_history(self, chat_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieves the chat history for a given chat_id.

        Args:
            chat_id: The ID of the chat.
            limit: If specified, retrieve only the last 'limit' messages.

        Returns:
            A list of message dictionaries, or an empty list if no history is found or Redis is unavailable.
        """
        if not self.redis_client:
            logger.error("Redis client not available. Cannot get history.")
            return []

        key = self._get_chat_key(chat_id)
        try:
            if limit is None or limit <= 0:
                # Retrieve all messages
                message_strings = self.redis_client.lrange(key, 0, -1)
            else:
                # Retrieve last 'limit' messages (lrange counts from the end with negative indices)
                message_strings = self.redis_client.lrange(key, -limit, -1)

            history = []
            for msg_str_bytes in message_strings:
                try:
                    history.append(json.loads(msg_str_bytes.decode('utf-8')))
                except json.JSONDecodeError:
                    logger.warning(f"Failed to decode JSON for a message in chat {chat_id}. Skipping message: {msg_str_bytes[:100]}") # Log first 100 chars
                except UnicodeDecodeError:
                    logger.warning(f"Failed to decode UTF-8 for a message in chat {chat_id}. Skipping message: {msg_str_bytes[:100]}")


            # Refresh TTL if history exists and TTL is configured
            if message_strings and self.ttl_seconds:
                self.redis_client.expire(key, self.ttl_seconds)
            return history
        except redis.exceptions.RedisError as e:
            logger.error(f"Redis error while getting history for chat {chat_id}: {e}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"Unexpected error while getting history for chat {chat_id}: {e}", exc_info=True)
            return []

    def add_message_to_history(self, chat_id: str, message: Dict[str, Any]):
        """
        Adds a message to the chat history and refreshes the TTL.

        Args:
            chat_id: The ID of the chat.
            message: The message dictionary (must include 'role', 'content').
                     'timestamp' will be added if not present.
        """
        if not self.redis_client:
            logger.error("Redis client not available. Cannot add message to history.")
            return

        key = self._get_chat_key(chat_id)

        if 'timestamp' not in message:
            message['timestamp'] = datetime.now(timezone.utc).isoformat()
        if 'role' not in message or 'content' not in message:
            logger.error(f"Message for chat {chat_id} is missing 'role' or 'content'. Message: {message}")
            return

        try:
            message_json = json.dumps(message)
            self.redis_client.rpush(key, message_json)
            if self.ttl_seconds:
                self.redis_client.expire(key, self.ttl_seconds)
            logger.debug(f"Added message to history for chat {chat_id}. History length: {self.redis_client.llen(key)}")
        except redis.exceptions.RedisError as e:
            logger.error(f"Redis error while adding message for chat {chat_id}: {e}", exc_info=True)
        except TypeError as e: # For json.dumps failure
            logger.error(f"Failed to serialize message to JSON for chat {chat_id}: {e}. Message: {message}", exc_info=True)
        except Exception as e:
            logger.error(f"Unexpected error while adding message for chat {chat_id}: {e}", exc_info=True)


    def clear_history(self, chat_id: str):
        """
        Clears the chat history for a given chat_id (deletes the Redis key).

        Args:
            chat_id: The ID of the chat.
        """
        if not self.redis_client:
            logger.error("Redis client not available. Cannot clear history.")
            return

        key = self._get_chat_key(chat_id)
        try:
            deleted_count = self.redis_client.delete(key)
            if deleted_count > 0:
                logger.info(f"Cleared history for chat {chat_id} (key: {key}).")
            else:
                logger.info(f"No history found to clear for chat {chat_id} (key: {key}).")
        except redis.exceptions.RedisError as e:
            logger.error(f"Redis error while clearing history for chat {chat_id}: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Unexpected error while clearing history for chat {chat_id}: {e}", exc_info=True)

    # `delete_history` is an alias for `clear_history` in this initial version.
    # It might diverge later if "archival" or other logic is added.
    delete_history = clear_history


# Example Usage (for testing purposes, typically not run directly like this)
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Attempt to get Redis connection details from environment variables
    # These would be set in your .env file or deployment environment
    redis_host = os.getenv('REDIS_HOST', 'localhost')
    redis_port = int(os.getenv('REDIS_PORT', '6379'))
    redis_password = os.getenv('REDIS_PASSWORD', None)
    redis_db = int(os.getenv('REDIS_DB', '0'))
    chat_ttl_str = os.getenv('REDIS_CHAT_HISTORY_TTL_SECONDS')
    chat_ttl = int(chat_ttl_str) if chat_ttl_str else None

    logger.info(f"Attempting to connect to Redis: host={redis_host}, port={redis_port}, db={redis_db}, TTL={chat_ttl or MemoryManager.DEFAULT_TTL_SECONDS}s")

    manager = MemoryManager(
        host=redis_host,
        port=redis_port,
        db=redis_db,
        password=redis_password,
        chat_history_ttl_seconds=chat_ttl
    )

    if not manager.redis_client:
        logger.error("MemoryManager could not connect to Redis. Exiting example.")
        exit(1)

    test_chat_id = "test_chat_123"
    logger.info(f"--- Testing MemoryManager for chat_id: {test_chat_id} ---")

    # Clear any old history for this test_chat_id
    logger.info(f"Clearing any existing history for {test_chat_id}...")
    manager.clear_history(test_chat_id)

    # Add some messages
    logger.info("Adding messages...")
    manager.add_message_to_history(test_chat_id, {"role": "user", "content": "Hello Katana!"})
    manager.add_message_to_history(test_chat_id, {"role": "assistant", "content": "Hello there! How can I help?"})
    manager.add_message_to_history(test_chat_id, {"role": "user", "content": "Tell me about conscious memory."})

    # Get history
    logger.info("Retrieving full history:")
    history = manager.get_history(test_chat_id)
    for msg in history:
        logger.info(f"  {msg}")

    # Get limited history
    logger.info("Retrieving last 2 messages:")
    limited_history = manager.get_history(test_chat_id, limit=2)
    for msg in limited_history:
        logger.info(f"  {msg}")

    # Test TTL (manual check in redis-cli: TTL chat_history:test_chat_123)
    logger.info(f"History for {test_chat_id} should have a TTL of {manager.ttl_seconds} seconds.")
    logger.info(f"You can check with: redis-cli TTL {manager._get_chat_key(test_chat_id)}")


    # Clear history again
    # logger.info(f"Clearing history for {test_chat_id} again...")
    # manager.clear_history(test_chat_id)
    # history_after_clear = manager.get_history(test_chat_id)
    # logger.info(f"History after clear (should be empty): {history_after_clear}")

    logger.info(f"--- Test complete for chat_id: {test_chat_id} ---")

    # Example of a message that would fail validation (if strict validation were added beyond logging)
    # manager.add_message_to_history(test_chat_id, {"sender": "user", "text": "Invalid format"})
    # manager.add_message_to_history(test_chat_id, {"role": "user", "content": {"complex": "object"}}) # This would be fine if content can be any JSON serializable
    manager.add_message_to_history(test_chat_id, {"role": "user", "content": "One last message before potential expiry."})
    logger.info(f"Current history length for {test_chat_id}: {len(manager.get_history(test_chat_id))}")

    logger.info("To test TTL expiration, wait for the configured TTL and then try to retrieve history.")
    logger.info(f"If TTL is {manager.ttl_seconds}s, after that time, get_history should return an empty list.")

    # Test handling of non-existent history
    non_existent_chat_id = "chat_does_not_exist_456"
    logger.info(f"Retrieving history for non-existent chat_id: {non_existent_chat_id}")
    non_existent_history = manager.get_history(non_existent_chat_id)
    logger.info(f"History for {non_existent_chat_id} (should be empty): {non_existent_history}")

    # Test adding a message to a new chat
    logger.info(f"Adding message to new chat_id: {non_existent_chat_id}")
    manager.add_message_to_history(non_existent_chat_id, {"role": "system", "content": "System initialized."})
    new_chat_history = manager.get_history(non_existent_chat_id)
    logger.info(f"History for {non_existent_chat_id} after adding message: {new_chat_history}")
    manager.clear_history(non_existent_chat_id) # Clean up

    # Test with TTL disabled (set to 0 or negative)
    logger.info("--- Testing MemoryManager with TTL disabled ---")
    manager_no_ttl = MemoryManager(
        host=redis_host,
        port=redis_port,
        db=redis_db,
        password=redis_password,
        chat_history_ttl_seconds=0 # Disable TTL
    )
    if manager_no_ttl.redis_client:
        test_chat_no_ttl = "test_chat_no_ttl_789"
        manager_no_ttl.clear_history(test_chat_no_ttl)
        manager_no_ttl.add_message_to_history(test_chat_no_ttl, {"role": "user", "content": "This chat should not expire."})
        logger.info(f"History for {test_chat_no_ttl}: {manager_no_ttl.get_history(test_chat_no_ttl)}")
        logger.info(f"Check TTL for {manager_no_ttl._get_chat_key(test_chat_no_ttl)} in redis-cli. Should be -1 (no TTL).")
        # manager_no_ttl.clear_history(test_chat_no_ttl) # Clean up
    else:
        logger.warning("Skipping no-TTL test as Redis connection failed for manager_no_ttl.")

    logger.info("--- MemoryManager example usage finished ---")

# Create __init__.py in src/memory/ if it doesn't exist, so it's recognized as a package
# (Although with src layout, direct imports like `from src.memory.memory_manager import MemoryManager`
# are often used from the project root, assuming src is in PYTHONPATH)
# For now, no __init__.py is created by this tool directly.
# If needed, it would be:
# create_file_with_block
# src/memory/__init__.py
# # This file makes Python treat the `memory` directory as a package.
# from .memory_manager import MemoryManager
# __all__ = ['MemoryManager']
