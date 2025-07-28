import click
import json
import os
import sys

# Add the app directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from katana_state import KatanaState

@click.group()
def cli():
    """A command-line interface for managing the Katana queue."""
    pass

@cli.command()
def status():
    """Displays the current status of the command queue."""
    # This is a simplified implementation. In a real-world scenario, you would
    # need a way to access the state of the running bot process.
    click.echo("Queue status functionality is not yet fully implemented.")
    # Example of how it could work if state was accessible:
    # try:
    #     with open("katana_state.json", "r") as f:
    #         state = json.load(f)
    #         queue = state.get("command_queue", [])
    #         if not queue:
    #             click.echo("The command queue is empty.")
    #         else:
    #             click.echo("Current command queue:")
    #             for command in queue:
    #                 click.echo(f"- {command}")
    # except FileNotFoundError:
    #     click.echo("Could not find Katana state file. Is the bot running?")

@cli.command()
@click.argument('command_id')
def status(command_id):
    """Displays the status of a specific command."""
    try:
        import requests
        response = requests.get(f"http://localhost:5001/command/{command_id}")
        response.raise_for_status()
        click.echo(json.dumps(response.json(), indent=2))
    except requests.exceptions.RequestException as e:
        click.echo(f"Error: {e}", err=True)

@cli.command()
@click.argument('command_id')
def cancel(command_id):
    """Cancels a command in the queue by its ID."""
    # This is a simplified implementation. In a real-world scenario, you would
    # need a way to access the state of the running bot process.
    click.echo(f"Attempting to cancel command: {command_id}")
    try:
        # This is not a robust way to share state between processes.
        # For a real application, consider using a database, a message queue (like Redis),
        # or another form of IPC to manage shared state.
        state = KatanaState()
        state.cancel_command(command_id)
        click.echo(f"Command {command_id} has been marked for cancellation.")
    except Exception as e:
        click.echo(f"Error canceling command: {e}", err=True)

@cli.command()
def flush():
    """Flushes the entire command queue."""
    click.echo("Flushing the command queue is not yet implemented.")

if __name__ == '__main__':
    cli()
