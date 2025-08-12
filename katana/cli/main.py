import click
import sys
from pathlib import Path

# This allows the CLI to be run from the root directory and find the 'katana' package
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

@click.group()
def cli():
    """Katana-CLI: A command-line interface for the Katana ecosystem."""
    pass

# This is a placeholder for where other command groups will be added
# For example, from wanderer_cli.py
from katana.cli.wanderer_cli import wanderer
cli.add_command(wanderer)

if __name__ == '__main__':
    cli()
