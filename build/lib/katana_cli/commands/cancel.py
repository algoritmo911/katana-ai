from .base import KatanaCommand
from katana_cli.utils.logger import get_logger

logger = get_logger(__name__)

class CancelTaskCommand(KatanaCommand):
    """Cancel the current active task."""
    name = "cancel"
    help = "Cancel the current active task"

    def run(self, args):
        logger.info("Canceling current task...")
