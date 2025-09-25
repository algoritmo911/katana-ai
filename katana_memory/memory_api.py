from typing import Optional, List, Dict, Any
from katana_memory.short_term.redis_cache import RedisCache
from katana_memory.long_term.neurovault import SupabaseMemoryCore

class MemoryManager:
    def __init__(self):
        """
        Initializes both short-term (Redis) and long-term (Supabase) memory managers.
        """
        self.short_term_memory = RedisCache()
        self.long_term_memory = SupabaseMemoryCore()

    # --- Short-Term Memory Methods ---

    async def remember(self, chat_id: int, text: str, ttl_seconds: int = 3600):
        """
        Remembers a piece of text for a specific chat_id in short-term memory (Redis).
        This is used for conversation history within a session.
        """
        await self.short_term_memory.store(chat_id, text, ttl_seconds)

    async def recall(self, chat_id: int) -> Optional[str]:
        """
        Recalls the full conversation history for a chat_id from short-term memory.
        """
        return await self.short_term_memory.retrieve(chat_id)

    async def forget(self, chat_id: int):
        """
        Forgets (deletes) the short-term memory for a specific chat_id.
        """
        await self.short_term_memory.delete(chat_id)

    # --- Long-Term Memory Methods ---

    async def store_long_term(self, summary: str, embedding: List[float], metadata: Optional[Dict[str, Any]] = None):
        """
        Stores a distilled memory (summary and embedding) into long-term memory (Supabase).
        """
        if self.long_term_memory.is_configured:
            await self.long_term_memory.add_memory(summary, embedding, metadata)
        else:
            print("[MemoryManager] Long-term memory is not configured. Skipping store.")

    async def recall_long_term(self, embedding: List[float], top_k: int = 5, match_threshold: float = 0.78) -> List[Dict[str, Any]]:
        """
        Recalls related memories from long-term memory based on semantic similarity.
        """
        if self.long_term_memory.is_configured:
            return await self.long_term_memory.find_related_memories(embedding, top_k, match_threshold)
        else:
            print("[MemoryManager] Long-term memory is not configured. Skipping recall.")
            return []

    # --- Connection Management ---

    async def close_connections(self):
        """
        Closes any open connections, such as the Redis connection.
        Supabase client does not require explicit connection closing with this library version.
        """
        await self.short_term_memory.close()
        # No need to close Supabase client explicitly.
        print("[MemoryManager] Closed short-term memory connections.")
