import os
from supabase import create_client, Client
from typing import List, Optional, Dict, Any

class SupabaseMemoryCore:
    """
    Handles the interaction with Supabase for storing and retrieving long-term memories.
    """
    def __init__(self):
        """
        Initializes the Supabase client.
        """
        self.supabase: Optional[Client] = None
        self.is_configured = False

        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            print("[NEUROVAULT WARNING] SUPABASE_URL or SUPABASE_KEY not found in environment variables. Neurovault will be disabled.")
        else:
            try:
                self.supabase = create_client(supabase_url, supabase_key)
                self.is_configured = True
                print("[NEUROVAULT INFO] Supabase client initialized successfully.")
            except Exception as e:
                print(f"[NEUROVAULT ERROR] Failed to initialize Supabase client: {e}")

    async def add_memory(self, summary: str, embedding: List[float], metadata: Optional[Dict[str, Any]] = None):
        """
        Adds a new memory (summary and its embedding) to the 'memories' table in Supabase.

        Args:
            summary: The text summary of the memory.
            embedding: The vector embedding of the summary.
            metadata: Optional dictionary for any other data to store with the memory.
        """
        if not self.is_configured or not self.supabase:
            print("[NEUROVAULT ERROR] Cannot add memory, Supabase is not configured.")
            return

        try:
            # The table is assumed to be named 'memories'
            # It should have at least 'content' (text) and 'embedding' (vector) columns.
            # A 'metadata' (jsonb) column is also recommended.
            data_to_insert = {
                'content': summary,
                'embedding': embedding,
                'metadata': metadata or {}
            }

            # Use asyncio.to_thread to run the synchronous Supabase client call in a separate thread,
            # preventing it from blocking the main async event loop.
            import asyncio
            response = await asyncio.to_thread(
                lambda: self.supabase.table('memories').insert(data_to_insert).execute()
            )

            print(f"[NEUROVAULT INFO] Successfully added memory to Supabase. Response: {response.data}")

        except Exception as e:
            print(f"[NEUROVAULT ERROR] Failed to add memory to Supabase: {e}")

    async def find_related_memories(self, embedding: List[float], top_k: int = 5, match_threshold: float = 0.78) -> List[Dict[str, Any]]:
        """
        Finds related memories in Supabase using vector similarity search.

        This function calls a Remote Procedure Call (RPC) in Supabase, which is expected
        to perform the vector search.

        Args:
            embedding: The vector embedding of the query.
            top_k: The maximum number of related memories to retrieve.
            match_threshold: The minimum similarity score for a memory to be considered a match.

        Returns:
            A list of memories that are similar to the query embedding.
        """
        if not self.is_configured or not self.supabase:
            print("[NEUROVAULT ERROR] Cannot find memories, Supabase is not configured.")
            return []

        try:
            # The RPC function is assumed to be named 'match_memories'.
            # It should accept a query_embedding, a match_threshold, and a match_count.
            # You need to set this up in your Supabase SQL editor. See example below.
            """
            -- Example SQL for the match_memories function
            -- Make sure you have the pgvector extension enabled in Supabase.
            -- create extension vector;
            --
            -- create table memories (
            --   id bigserial primary key,
            --   content text,
            --   embedding vector(1536), -- Ensure the dimension matches your embedding model (1536 for ada-002)
            --   metadata jsonb,
            --   created_at timestamptz default now()
            -- );
            --
            -- create or replace function match_memories (
            --   query_embedding vector(1536),
            --   match_threshold float,
            --   match_count int
            -- )
            -- returns table (
            --   id bigint,
            --   content text,
            --   similarity float
            -- )
            -- language sql stable
            -- as $$
            --   select
            --     memories.id,
            --     memories.content,
            --     1 - (memories.embedding <=> query_embedding) as similarity
            --   from memories
            --   where 1 - (memories.embedding <=> query_embedding) > match_threshold
            --   order by similarity desc
            --   limit match_count;
            -- $$;
            """
            import asyncio

            response = await asyncio.to_thread(
                lambda: self.supabase.rpc('match_memories', {
                    'query_embedding': embedding,
                    'match_threshold': match_threshold,
                    'match_count': top_k,
                }).execute()
            )

            if response.data:
                print(f"[NEUROVAULT INFO] Found {len(response.data)} related memories.")
                return response.data
            else:
                print("[NEUROVAULT INFO] No related memories found above the threshold.")
                return []

        except Exception as e:
            print(f"[NEUROVAULT ERROR] Error calling RPC 'match_memories': {e}")
            return []
