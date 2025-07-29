import click
import json
from rich.console import Console
from rich.table import Table
from katana.core.cli_logic.log import get_logs

import asyncio

@click.command()
@click.option("--last", "-l", default=10, help="The number of logs to show.")
@click.option("--error", "-e", is_flag=True, help="Show only error logs.")
@click.option("--today", "-t", is_flag=True, help="Show only logs from today.")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format.")
@click.pass_context
def log(ctx, last, error, today, output_json):
    """
    Show the logs.
    """
    console = Console()
    api_client = ctx.obj.get("api_client")

    if not api_client:
        console.print("Not connected to a Katana core. Please provide a WebSocket endpoint using the --ws-endpoint option or by setting it in the config file.")
        # Fallback to mock data
        logs = get_logs(last, error, today)
    else:
        try:
            logs = asyncio.run(api_client.send_command("log", {"last": last, "error": error, "today": today}))
        except Exception as e:
            console.print(f"Error connecting to Katana core: {e}")
            return

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
