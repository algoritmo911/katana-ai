import click
import asyncio
from rich.console import Console

@click.command()
@click.argument("script")
@click.option("--bg", is_flag=True, help="Run the task in the background.")
@click.pass_context
def run(ctx, script, bg):
    """
    Run a script.
    """
    console = Console()
    api_client = ctx.obj.get("api_client")

    if not api_client:
        console.print("Not connected to a Katana core. Please provide a WebSocket endpoint using the --ws-endpoint option or by setting it in the config file.")
        return

    try:
        result = asyncio.run(api_client.send_command("run", {"script": script, "bg": bg}))
        if bg:
            console.print(f"Task submitted with ID: {result.get('task_id')}")
        else:
            console.print(result)
    except Exception as e:
        console.print(f"Error: {e}")
