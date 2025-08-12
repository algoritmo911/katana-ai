import redis.asyncio as redis
import json

class KnowledgeQueueClient:
    """
    Client for the queue that feeds extracted content into the Noosfera
    for cognitive processing.
    """
    def __init__(self, host='localhost', port=6379, queue_name='noosfera_cognitive_queue'):
        self.redis = redis.Redis(host=host, port=port) # No decode_responses, handle bytes
        self.queue_name = queue_name

    async def submit_content(self, source_url: str, content: str):
        """
        Submits extracted content to the knowledge queue for processing.
        """
        payload = {
            "source_url": source_url,
            "content": content
        }
        # json.dumps produces a string, which needs to be encoded to bytes for redis
        await self.redis.lpush(self.queue_name, json.dumps(payload).encode('utf-8'))
        print(f"Submitted content from {source_url} to knowledge queue.")
