import logging
import sys

def setup_logger():
    """Настраивает и конфигурирует глобальный логгер."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )
    logger = logging.getLogger("HydraObserver")
    logger.info("Логгер успешно настроен.")
