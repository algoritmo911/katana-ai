class GraphDiff:
    def __init__(self, added, removed, changed):
        self.added = added
        self.removed = removed
        self.changed = changed

    def __repr__(self):
        return f"GraphDiff(added={len(self.added)}, removed={len(self.removed)}, changed={len(self.changed)})"

def diff_graphs(old_graph, new_graph):
    old_ids = set(old_graph._commands.keys())
    new_ids = set(new_graph._commands.keys())

    added_ids = new_ids - old_ids
    removed_ids = old_ids - new_ids
    common_ids = old_ids & new_ids

    added = [new_graph.get_command(cmd_id) for cmd_id in added_ids]
    removed = [old_graph.get_command(cmd_id) for cmd_id in removed_ids]

    changed = []
    for cmd_id in common_ids:
        old_cmd = old_graph.get_command(cmd_id)
        new_cmd = new_graph.get_command(cmd_id)
        if old_cmd.status != new_cmd.status:
            changed.append(new_cmd)

    return GraphDiff(added, removed, changed)
