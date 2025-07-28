import click
from katana.graph.command_graph import CommandGraph

@click.group()
def graph():
    """Commands for interacting with the command graph."""
    pass

@graph.command()
@click.option('--path', default='command_graph.json', help='Path to the command graph file.')
def show(path):
    """Visualizes the command graph."""
    graph = CommandGraph()
    try:
        graph.load_from_file(path)
        graph.visualize()
    except FileNotFoundError:
        click.echo(f"Error: Command graph file not found at '{path}'")

if __name__ == '__main__':
    graph()
