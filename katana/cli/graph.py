import click
from katana.graph.command_graph import CommandGraph
from katana.graph.snapshot_store import SnapshotStore
from katana.graph.graph_diff import diff_graphs

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

@graph.group()
def snapshot():
    """Commands for managing command graph snapshots."""
    pass

@snapshot.command()
@click.option('--name', required=True, help='Name of the snapshot.')
@click.option('--path', default='command_graph.json', help='Path to the command graph file.')
def save(name, path):
    """Saves a snapshot of the command graph."""
    store = SnapshotStore()
    graph = CommandGraph()
    try:
        graph.load_from_file(path)
        store.save_snapshot(graph, name)
        click.echo(f"Snapshot '{name}' saved.")
    except FileNotFoundError:
        click.echo(f"Error: Command graph file not found at '{path}'")

@snapshot.command(name="list")
def list_snapshots():
    """Lists all available snapshots."""
    store = SnapshotStore()
    snapshots = store.list_snapshots()
    if not snapshots:
        click.echo("No snapshots found.")
        return
    for snap in snapshots:
        click.echo(snap)

@graph.command()
@click.option('--from', 'from_snap', required=True, help='The starting snapshot.')
@click.option('--to', 'to_snap', required=True, help='The ending snapshot.')
def diff(from_snap, to_snap):
    """Compares two snapshots and shows the differences."""
    store = SnapshotStore()
    try:
        from_graph = store.load_snapshot(from_snap)
        to_graph = store.load_snapshot(to_snap)
        diff_result = diff_graphs(from_graph, to_graph)
        click.echo(f"Added: {len(diff_result.added)}")
        for cmd in diff_result.added:
            click.echo(f"  - {cmd.id} ({cmd.type})")
        click.echo(f"Removed: {len(diff_result.removed)}")
        for cmd in diff_result.removed:
            click.echo(f"  - {cmd.id} ({cmd.type})")
        click.echo(f"Changed: {len(diff_result.changed)}")
        for cmd in diff_result.changed:
            click.echo(f"  - {cmd.id} ({cmd.type}) - Status: {cmd.status}")
    except FileNotFoundError as e:
        click.echo(f"Error: Snapshot not found. {e}")

@graph.command()
@click.option('--to', 'to_snap', required=True, help='The snapshot to travel to.')
@click.option('--path', default='command_graph.json', help='Path to the command graph file.')
def time_travel(to_snap, path):
    """Travels to a specific snapshot."""
    store = SnapshotStore()
    try:
        graph = store.load_snapshot(to_snap)
        graph.save_to_file(path)
        click.echo(f"Time traveled to snapshot '{to_snap}'.")
    except FileNotFoundError:
        click.echo(f"Error: Snapshot '{to_snap}' not found.")


if __name__ == '__main__':
    graph()
