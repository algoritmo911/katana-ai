import click
from rich.console import Console
from katana.core.cli_logic.flush import flush_system

@click.command()
@click.option("--force", is_flag=True, help="Force the flush without confirmation.")
def flush(force):
    """
    Flush the system.
    """
    console = Console()

    if not force:
        if not click.confirm("Are you sure you want to flush the system?"):
            console.print("Flush cancelled.")
            return

    if flush_system():
        console.print("Flushing cache...")
        console.print("Flushing logs...")
        console.print("Flushing task queue...")
        console.print("✅ System flushed.")
    else:
        console.print("⚠️ Flush failed.")
