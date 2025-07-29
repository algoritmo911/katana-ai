class KatanaCommand:
    """Base class for Katana CLI commands."""
    name = None
    help = None

    def __init__(self, parser):
        self.parser = parser

    def run(self, args):
        raise NotImplementedError
