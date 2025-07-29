import click
import json
from rich.console import Console
from rich.table import Table
from katana.core.cli_logic.history import get_history

import asyncio

@click.command()
@click.option("--user", "-u", help="Filter by user.")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format.")
@click.pass_context
def history(ctx, user, output_json):
    """
    Show the command history.
    """
    console = Console()
    api_client = ctx.obj.get("api_client")

    if not api_client:
        console.print("Not connected to a Katana core. Please provide a WebSocket endpoint using the --ws-endpoint option or by setting it in the config file.")
        # Fallback to mock data
        history_data = get_history(user)
    else:
        try:
            history_data = asyncio.run(api_client.send_command("history", {"user": user}))
        except Exception as e:
            console.print(f"Error connecting to Katana core: {e}")
            return

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
