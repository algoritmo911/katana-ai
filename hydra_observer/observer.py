import asyncio
import logging
from prometheus_client import start_http_server
from hydra_observer.telemetry.logger import setup_logger
from hydra_observer.telemetry.metrics_collector import MetricsCollector
from hydra_observer.watchers.agent_watcher import AgentWatcher
from hydra_observer.watchers.command_watcher import CommandWatcher
from hydra_observer.probes.heartbeat_probe import HeartbeatProbe
from hydra_observer.probes.latency_probe import LatencyProbe

# Настройка логгера
setup_logger()
logger = logging.getLogger(__name__)

async def main():
    """Главная функция для запуска всех компонентов Hydra Observer."""
    logger.info("Запуск Hydra Observer...")

    # Запуск Prometheus HTTP-сервера
    start_http_server(9100)
    logger.info("Prometheus-сервер запущен на порту 9100.")

    # Инициализация и запуск сборщика метрик
    metrics_collector = MetricsCollector()
    asyncio.create_task(metrics_collector.collect_metrics())

    # Инициализация и запуск наблюдателей
    agent_watcher = AgentWatcher()
    command_watcher = CommandWatcher()
    asyncio.create_task(agent_watcher.watch())
    asyncio.create_task(command_watcher.watch())

    # Инициализация и запуск пробников
    heartbeat_probe = HeartbeatProbe(interval=10)
    latency_probe = LatencyProbe(interval=5)
    asyncio.create_task(heartbeat_probe.start())
    asyncio.create_task(latency_probe.start())

    logger.info("Все компоненты Hydra Observer успешно запущены.")

    # Бесконечный цикл для поддержания работы
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Hydra Observer остановлен.")
    except Exception as e:
        logger.error(f"Критическая ошибка в Hydra Observer: {e}", exc_info=True)
