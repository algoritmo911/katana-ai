from typing import Optional
from katana_memory.short_term.redis_cache import RedisCache

class MemoryManager:
    def __init__(self):
        self.short_term_memory = RedisCache()

    async def remember(self, chat_id: int, text: str, ttl_seconds: int = 3600):
        """
        Remembers a piece of text for a specific chat_id in short-term memory.
        """
        await self.short_term_memory.store(chat_id, text, ttl_seconds)

    async def recall(self, chat_id: int) -> Optional[str]:
        """
        Recalls a piece of text for a specific chat_id from short-term memory.
        """
        return await self.short_term_memory.retrieve(chat_id)

    async def forget(self, chat_id: int):
        """
        Forgets (deletes) the memory for a specific chat_id from short-term memory.
        """
        await self.short_term_memory.delete(chat_id)

    async def close_connections(self):
        """
        Closes any open connections, like the Redis connection.
        """
        await self.short_term_memory.close()
