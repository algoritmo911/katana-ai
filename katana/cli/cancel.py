import click
from rich.console import Console
from katana.core.cli_logic.cancel import cancel_task

import asyncio

@click.command()
@click.argument("task_id")
@click.pass_context
def cancel(ctx, task_id):
    """
    Cancel a task by its ID.
    """
    console = Console()
    api_client = ctx.obj.get("api_client")

    if not api_client:
        console.print("Not connected to a Katana core. Please provide a WebSocket endpoint using the --ws-endpoint option or by setting it in the config file.")
        # Fallback to mock data
        if cancel_task(task_id):
            console.print(f"✅ Task {task_id} cancelled")
        else:
            console.print("⚠️ Task not found")
    else:
        try:
            result = asyncio.run(api_client.send_command("cancel", {"task_id": task_id}))
            if result.get("success"):
                console.print(f"✅ Task {task_id} cancelled")
            else:
                console.print(f"⚠️ {result.get('error', 'Task not found')}")
        except Exception as e:
            console.print(f"Error connecting to Katana core: {e}")
            return
