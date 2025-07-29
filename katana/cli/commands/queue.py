import click
import json
from rich.console import Console
from rich.table import Table
from katana.core.cli_logic.queue import get_queue

import asyncio

@click.command()
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format.")
@click.pass_context
def queue(ctx, output_json):
    """
    Show the command queue.
    """
    console = Console()
    api_client = ctx.obj.get("api_client")

    if not api_client:
        console.print("Not connected to a Katana core. Please provide a WebSocket endpoint using the --ws-endpoint option or by setting it in the config file.")
        # Fallback to mock data
        command_queue = get_queue()
    else:
        try:
            command_queue = asyncio.run(api_client.send_command("queue", {}))
        except Exception as e:
            console.print(f"Error connecting to Katana core: {e}")
            return

    if output_json:
        console.print(json.dumps(command_queue, indent=4))
        return

    table = Table(title="Katana AI Command Queue")
    table.add_column("Command")
    table.add_column("Priority")

    for command in command_queue:
        table.add_row(command["command"], str(command["priority"]))

    console.print(table)
