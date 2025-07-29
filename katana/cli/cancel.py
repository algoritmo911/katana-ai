import click
from rich.console import Console
from katana.core.cli_logic.cancel import cancel_task

@click.command()
@click.argument("task_id")
def cancel(task_id):
    """
    Cancel a task by its ID.
    """
    console = Console()

    if cancel_task(task_id):
        console.print(f"✅ Task {task_id} cancelled")
    else:
        console.print("⚠️ Task not found")
