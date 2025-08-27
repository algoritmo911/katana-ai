import json
from typing import Any, Optional

from redis.asyncio import Redis
from loguru import logger

from src.katana.services.memory import AbstractMemoryService
from src.katana.configs.settings import settings

class RedisMemoryService(AbstractMemoryService):
    """
    A concrete implementation of the memory service using Redis as the backend.

    This class handles the specifics of interacting with Redis, including
    connection management and data serialization (using JSON).
    """

    _client: Optional[Redis] = None

    async def _get_client(self) -> Redis:
        """Initializes and returns the Redis client, ensuring a single instance."""
        if self._client is None:
            logger.info(f"Initializing Redis client for URL: {settings.redis_url}")
            # from_url is a convenient way to create a client from a connection string
            self._client = Redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True # Automatically decode responses to UTF-8
            )
        return self._client

    async def get(self, key: str) -> Optional[Any]:
        """
        Retrieves a value from Redis. Assumes the value is stored as a JSON string.
        """
        client = await self._get_client()
        logger.debug(f"REDIS GET: key='{key}'")
        value_str = await client.get(key)
        if value_str:
            try:
                return json.loads(value_str)
            except json.JSONDecodeError:
                logger.warning(f"Failed to decode JSON for key '{key}'. Returning raw value.")
                return value_str
        return None

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """
        Saves a value to Redis after serializing it to a JSON string.
        """
        client = await self._get_client()
        logger.debug(f"REDIS SET: key='{key}', ttl={ttl_seconds}s")
        serialized_value = json.dumps(value)
        await client.set(key, serialized_value, ex=ttl_seconds)

    async def delete(self, key: str) -> bool:
        """
        Deletes a key from Redis. `unlink` is often preferred as it's non-blocking.
        """
        client = await self._get_client()
        logger.debug(f"REDIS DEL: key='{key}'")
        # `unlink` performs the actual memory reclaiming in a separate thread.
        deleted_count = await client.unlink(key)
        return deleted_count > 0
