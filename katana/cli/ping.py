import click
from rich.console import Console
from katana.core.cli_logic.ping import ping as core_ping

import asyncio

@click.command()
@click.pass_context
def ping(ctx):
    """
    Ping the Katana AI.
    """
    console = Console()
    api_client = ctx.obj.get("api_client")

    if not api_client:
        console.print("Not connected to a Katana core. Please provide a WebSocket endpoint using the --ws-endpoint option or by setting it in the config file.")
        # Fallback to mock data
        console.print(core_ping())
    else:
        try:
            result = asyncio.run(api_client.send_command("ping", {}))
            console.print(result.get("message", "✅ Pong!"))
        except Exception as e:
            console.print(f"Error connecting to Katana core: {e}")
            return
