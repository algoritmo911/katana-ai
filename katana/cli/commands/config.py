import click
import json
from rich.console import Console
from rich.table import Table
from katana.core.cli_logic.config import set_config_value, show_config

@click.group()
def config():
    """
    Manage the CLI configuration.
    """
    pass

@config.command()
@click.argument("key", type=click.Choice(["endpoint", "ws_endpoint"]))
@click.argument("value")
def set(key, value):
    """
    Set a configuration key-value pair.
    """
    console = Console()
    set_config_value(key, value)
    console.print(f"✅ Config value '{key}' set to '{value}'.")

@config.command()
def show():
    """
    Show the current configuration.
    """
    console = Console()
    config = show_config()
    if not config:
        console.print("No configuration set.")
        return

    table = Table(title="Katana AI Configuration")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="magenta")

    for key, value in config.items():
        table.add_row(key, str(value))

    console.print(table)
