import click
import json
from rich.console import Console
from rich.table import Table
from katana.core.cli_logic.status import get_status

@click.command()
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format.")
@click.pass_context
def status(ctx, output_json):
    """
    Get the status of the Katana AI.
    """
    console = Console()
    if not ctx.obj.get('auth_token'):
        console.print("🔒 Authentication required. Please provide a token using the --auth-token option or by creating a ~/.katana/cli_auth.json file.")
        return

    status_data = get_status()

    if output_json:
        console.print(json.dumps(status_data, indent=4))
        return

    table = Table(title="Katana AI Status")
    table.add_column("Attribute", style="cyan")
    table.add_column("Value", style="magenta")

    table.add_row("Status", status_data["status"])
    table.add_row("Active Tasks", str(status_data["active_tasks"]))

    command_queue_table = Table(title="Command Queue")
    command_queue_table.add_column("Command")
    command_queue_table.add_column("Priority")

    for command in status_data["command_queue"]:
        command_queue_table.add_row(command["command"], str(command["priority"]))

    errors_table = Table(title="Last 3 Errors")
    errors_table.add_column("Error")

    for error in status_data["errors"][:3]:
        errors_table.add_row(error)

    console.print(table)
    console.print(command_queue_table)
    console.print(errors_table)
