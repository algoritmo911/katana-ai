import click
from rich.console import Console
from katana.core.cli_logic.flush import flush_system

import asyncio

@click.command()
@click.option("--force", is_flag=True, help="Force the flush without confirmation.")
@click.pass_context
def flush(ctx, force):
    """
    Flush the system.
    """
    console = Console()
    api_client = ctx.obj.get("api_client")

    if not force:
        if not click.confirm("Are you sure you want to flush the system?"):
            console.print("Flush cancelled.")
            return

    if not api_client:
        console.print("Not connected to a Katana core. Please provide a WebSocket endpoint using the --ws-endpoint option or by setting it in the config file.")
        # Fallback to mock data
        if flush_system():
            console.print("Flushing cache...")
            console.print("Flushing logs...")
            console.print("Flushing task queue...")
            console.print("✅ System flushed.")
        else:
            console.print("⚠️ Flush failed.")
    else:
        try:
            result = asyncio.run(api_client.send_command("flush", {}))
            if result.get("success"):
                console.print("✅ System flushed.")
            else:
                console.print(f"⚠️ {result.get('error', 'Flush failed.')}")
        except Exception as e:
            console.print(f"Error connecting to Katana core: {e}")
            return
