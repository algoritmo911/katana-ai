from abc import ABC, abstractmethod

class StorageAdapter(ABC):
    """Abstract base class for storage adapters."""

    @abstractmethod
    def save(self, user_id: int, data: dict) -> None:
        """Saves user data."""
        pass

    @abstractmethod
    def load(self, user_id: int) -> dict | None:
        """Loads user data."""
        pass

    @abstractmethod
    def list_versions(self, user_id: int) -> list[str]:
        """Lists available versions of a user's profile."""
        pass
