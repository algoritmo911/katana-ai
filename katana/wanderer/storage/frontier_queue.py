import redis.asyncio as redis

class FrontierQueueClient:
    """
    Клиент для управления очередью исследования (frontier) в Redis.
    Использует сортированные множества (sorted sets) для приоритизации.
    """
    def __init__(self, host='localhost', port=6379, queue_name='wanderer_frontier'):
        self.redis = redis.Redis(host=host, port=port, decode_responses=True)
        self.queue_name = queue_name

    async def add_url(self, url: str, priority: float):
        """Добавляет URL в очередь. Более высокий приоритет означает более раннее сканирование."""
        await self.redis.zadd(self.queue_name, {url: priority})

    async def get_next_url(self) -> str | None:
        """Извлекает и удаляет URL с наивысшим приоритетом из очереди."""
        # ZPOPMIN атомарно извлекает элемент с наименьшим score. Мы используем
        # отрицательные приоритеты, чтобы наивысший приоритет (например, 0.9)
        # стал наименьшим score (-0.9).
        result = await self.redis.zpopmax(self.queue_name)
        if result:
            url, score = result[0]
            return url
        return None

    async def get_queue_size(self) -> int:
        return await self.redis.zcard(self.queue_name)
