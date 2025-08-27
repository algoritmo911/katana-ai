from abc import ABC, abstractmethod
from typing import Any, Optional

class AbstractMemoryService(ABC):
    """
    Abstract base class for a key-value memory/cache service.

    This defines the contract for any service that provides short-term memory
    or caching capabilities. Command handlers and other components will depend
    on this abstraction, not on a concrete implementation (like Redis or an
    in-memory dictionary). This adheres to the Dependency Inversion Principle.
    """

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """
        Retrieves a value from the memory service by its key.

        Args:
            key: The key of the item to retrieve.

        Returns:
            The value associated with the key if it exists, otherwise None.
        """
        raise NotImplementedError

    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """
        Saves a value in the memory service with an optional time-to-live (TTL).

        Args:
            key: The key under which to store the value.
            value: The value to store. It should be serializable (e.g., str, bytes, dict).
            ttl_seconds: Optional number of seconds until the key expires.
                         If None or 0, the key should persist indefinitely.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Deletes a key-value pair from the memory service.

        Args:
            key: The key of the item to delete.

        Returns:
            True if the key was deleted, False if the key did not exist.
        """
        raise NotImplementedError
