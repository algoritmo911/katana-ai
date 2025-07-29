import click
import json
from rich.console import Console
from rich.table import Table
from katana.core.cli_logic.queue import get_queue

@click.command()
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format.")
def queue(output_json):
    """
    Show the command queue.
    """
    console = Console()
    command_queue = get_queue()

    if output_json:
        console.print(json.dumps(command_queue, indent=4))
        return

    table = Table(title="Katana AI Command Queue")
    table.add_column("Command")
    table.add_column("Priority")

    for command in command_queue:
        table.add_row(command["command"], str(command["priority"]))

    console.print(table)
