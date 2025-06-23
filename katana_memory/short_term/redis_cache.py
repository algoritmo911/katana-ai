import redis.asyncio as redis
import os
from typing import Optional

class RedisCache:
    def __init__(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_client = redis.from_url(redis_url)

    async def store(self, chat_id: int, text: str, ttl_seconds: int = 3600):
        """
        Stores text in Redis with a specific chat_id as the key.
        The data will expire after ttl_seconds.
        """
        await self.redis_client.setex(f"chat:{chat_id}", ttl_seconds, text)

    async def retrieve(self, chat_id: int) -> Optional[str]:
        """
        Retrieves text from Redis based on chat_id.
        Returns the text if found, otherwise None.
        """
        data = await self.redis_client.get(f"chat:{chat_id}")
        return data.decode('utf-8') if data else None

    async def delete(self, chat_id: int):
        """
        Deletes data from Redis for a specific chat_id.
        """
        await self.redis_client.delete(f"chat:{chat_id}")

    async def close(self):
        """
        Closes the Redis connection.
        """
        await self.redis_client.close()
