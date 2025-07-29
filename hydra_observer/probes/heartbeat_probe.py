import asyncio
import logging
from prometheus_client import Counter

logger = logging.getLogger(__name__)

class HeartbeatProbe:
    """
    Периодически отправляет "heartbeat" для проверки живости системы.
    Использует счетчик Prometheus для отслеживания количества heartbeat-ов.
    """

    def __init__(self, interval: int = 10):
        """
        Инициализирует пробник.
        :param interval: Интервал в секундах для отправки heartbeat.
        """
        self.interval = interval
        self.heartbeat_counter = Counter("hydra_heartbeat_total", "Total number of heartbeats")
        logger.info(f"Heartbeat-пробник инициализирован с интервалом {self.interval} секунд.")

    async def start(self):
        """
        Запускает асинхронную отправку heartbeat-ов.
        """
        logger.info("Heartbeat-пробник запущен.")
        while True:
            await asyncio.sleep(self.interval)
            self.heartbeat_counter.inc()
            logger.info("❤️ Heartbeat! Система в порядке.")
