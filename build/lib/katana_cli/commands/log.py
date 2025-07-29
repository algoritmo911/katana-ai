from .base import KatanaCommand
from katana_cli.utils.logger import get_logger

logger = get_logger(__name__)

class LogCommand(KatanaCommand):
    """Show last 10 logs."""
    name = "log"
    help = "Show last 10 logs"

    def run(self, args):
        logger.info("Showing last 10 logs...")
