import click
from rich.console import Console
from katana.core.cli_logic.ping import ping as core_ping

@click.command()
def ping():
    """
    Ping the Katana AI.
    """
    console = Console()
    console.print(core_ping())
