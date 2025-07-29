import json
from .base import KatanaCommand

class StatusCommand(KatanaCommand):
    """Show system status."""
    name = "status"
    help = "Show system status"

    def run(self, args):
        status = self.get_status()
        print(json.dumps(status, indent=4))

    def get_status(self):
        return {
            "uptime": "1h 22m",
            "tasks": 0,
            "version": "0.0.1-dev"
        }
