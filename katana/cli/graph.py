import click
from katana.graph.command_graph import CommandGraph

@click.group()
def graph():
    """Commands for interacting with the command graph."""
    pass

@graph.command()
@click.option('--path', default='command_graph.json', help='Path to the command graph file.')
@click.option('--format', type=click.Choice(['rich', 'dot']), default='rich', help='Output format.')
@click.option('--output', help='Path to the output file.')
def show(path, format, output):
    """Visualizes the command graph."""
    graph = CommandGraph()
    try:
        graph.load_from_file(path)
        if format == 'rich':
            if output:
                click.echo("Error: --output is not supported for rich format.")
                return
            graph.visualize()
        elif format == 'dot':
            dot_data = graph.to_dot()
            if output:
                with open(output, "w") as f:
                    f.write(dot_data)
            else:
                click.echo(dot_data)
    except FileNotFoundError:
        click.echo(f"Error: Command graph file not found at '{path}'")

@graph.command()
@click.option('--path', default='command_graph.json', help='Path to the command graph file.')
def errors(path):
    """Shows only the commands with status 'ERROR'."""
    graph = CommandGraph()
    try:
        graph.load_from_file(path)
        error_commands = graph.get_by_status("ERROR")
        if not error_commands:
            click.echo("No errors found in the command graph.")
            return
        for cmd in error_commands:
            click.echo(f"ID: {cmd.id}, Type: {cmd.type}, Module: {cmd.module}")
    except FileNotFoundError:
        click.echo(f"Error: Command graph file not found at '{path}'")

@graph.command()
@click.argument('path')
def save(path):
    """Saves the command graph to a file."""
    # This is a placeholder, as the graph is not yet integrated with the bot
    click.echo("Saving the command graph is not yet implemented.")

@graph.command()
@click.argument('path')
def load(path):
    """Loads the command graph from a file."""
    # This is a placeholder, as the graph is not yet integrated with the bot
    click.echo("Loading the command graph is not yet implemented.")

@graph.command()
@click.argument('command_id')
@click.option('--path', default='command_graph.json', help='Path to the command graph file.')
def trace(command_id, path):
    """Traces the execution path from a command to its root."""
    graph = CommandGraph()
    try:
        graph.load_from_file(path)
        path_to_root = graph.trace_path_to(command_id)
        if not path_to_root:
            click.echo(f"Command with ID '{command_id}' not found or it is a root.")
            return
        click.echo(" -> ".join(cmd.id for cmd in path_to_root))
    except FileNotFoundError:
        click.echo(f"Error: Command graph file not found at '{path}'")


if __name__ == '__main__':
    graph()
