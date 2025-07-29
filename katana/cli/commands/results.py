import click
import asyncio
from rich.console import Console

@click.command()
@click.argument("task_id")
@click.pass_context
def results(ctx, task_id):
    """
    Get the results of a task.
    """
    console = Console()
    api_client = ctx.obj.get("api_client")

    if not api_client:
        console.print("Not connected to a Katana core. Please provide a WebSocket endpoint using the --ws-endpoint option or by setting it in the config file.")
        return

    try:
        result = asyncio.run(api_client.send_command("results", {"task_id": task_id}))
        console.print(result)
    except Exception as e:
        console.print(f"Error: {e}")
