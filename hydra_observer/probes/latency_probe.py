import asyncio
import logging
import time
from prometheus_client import Histogram

logger = logging.getLogger(__name__)

class LatencyProbe:
    """
    Измеряет и отслеживает задержки выполнения операций.
    Использует гистограмму Prometheus для сбора данных о задержках.
    """

    def __init__(self, interval: int = 5):
        """
        Инициализирует пробник задержек.
        :param interval: Интервал в секундах для проведения измерений.
        """
        self.interval = interval
        # Гистограмма для измерения распределения задержек
        self.latency_histogram = Histogram(
            "hydra_operation_latency_seconds",
            "Latency of a simulated operation in seconds"
        )
        logger.info(f"Пробник задержек инициализирован с интервалом {self.interval} секунд.")

    async def measure_latency(self):
        """
        Имитирует выполнение операции и измеряет ее задержку.
        """
        start_time = time.time()
        # Имитация асинхронной операции
        await asyncio.sleep(0.1 + (time.time() % 0.2))  # Динамическая задержка
        end_time = time.time()
        latency = end_time - start_time
        self.latency_histogram.observe(latency)
        logger.debug(f"Измерена задержка: {latency:.4f} секунд.")

    async def start(self):
        """
        Запускает периодическое измерение задержек.
        """
        logger.info("Пробник задержек запущен.")
        while True:
            await self.measure_latency()
            await asyncio.sleep(self.interval)
