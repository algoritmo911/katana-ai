import asyncio
import logging
import psutil
from prometheus_client import Gauge

logger = logging.getLogger(__name__)

class MetricsCollector:
    """
    Сборщик системных метрик (CPU, RAM) с использованием psutil.
    Публикует метрики в формате, совместимом с Prometheus.
    """

    def __init__(self):
        """Инициализирует метрики Prometheus."""
        self.cpu_usage = Gauge("hydra_cpu_usage_percent", "CPU usage percentage")
        self.ram_usage = Gauge("hydra_ram_usage_percent", "RAM usage percentage")
        logger.info("Сборщик метрик инициализирован.")

    async def collect_metrics(self, interval: int = 5):
        """
        Асинхронно собирает и обновляет метрики с заданным интервалом.
        """
        logger.info(f"Сбор метрик будет производиться каждые {interval} секунд.")
        while True:
            try:
                # Сбор метрик CPU
                cpu_percent = psutil.cpu_percent(interval=None)
                self.cpu_usage.set(cpu_percent)

                # Сбор метрик RAM
                ram_percent = psutil.virtual_memory().percent
                self.ram_usage.set(ram_percent)

                logger.debug(f"Собраны метрики: CPU={cpu_percent}%, RAM={ram_percent}%")

            except Exception as e:
                logger.error(f"Ошибка при сборе метрик: {e}", exc_info=True)

            await asyncio.sleep(interval)
