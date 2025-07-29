import click
import json
from rich.console import Console
from rich.table import Table
from katana.core.cli_logic.history import get_history

@click.command()
@click.option("--user", "-u", help="Filter by user.")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format.")
def history(user, output_json):
    """
    Show the command history.
    """
    console = Console()
    history_data = get_history(user)

    if output_json:
        console.print(json.dumps(history_data, indent=4))
        return

    table = Table(title="Katana AI Command History")
    table.add_column("Timestamp", style="cyan")
    table.add_column("User", style="magenta")
    table.add_column("Command", style="green")

    for entry in history_data:
        table.add_row(entry["timestamp"], entry["user"], entry["command"])

    console.print(table)
