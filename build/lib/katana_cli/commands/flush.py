from .base import KatanaCommand
from katana_cli.utils.logger import get_logger

logger = get_logger(__name__)

class FlushCommand(KatanaCommand):
    """Flush temporary data/logs."""
    name = "flush"
    help = "Flush temporary data/logs"

    def run(self, args):
        logger.info("Flushing temporary data...")
