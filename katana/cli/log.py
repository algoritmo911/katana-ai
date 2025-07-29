import click
import json
from rich.console import Console
from rich.table import Table
from katana.core.cli_logic.log import get_logs

@click.command()
@click.option("--last", "-l", default=10, help="The number of logs to show.")
@click.option("--error", "-e", is_flag=True, help="Show only error logs.")
@click.option("--today", "-t", is_flag=True, help="Show only logs from today.")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format.")
def log(last, error, today, output_json):
    """
    Show the logs.
    """
    console = Console()
    logs = get_logs(last, error, today)

    if output_json:
        console.print(json.dumps(logs, indent=4))
        return

    table = Table(title="Katana AI Logs")
    table.add_column("Timestamp", style="cyan")
    table.add_column("Level", style="magenta")
    table.add_column("Message", style="green")

    for log_entry in logs:
        table.add_row(log_entry["timestamp"], log_entry["level"], log_entry["message"])

    console.print(table)
