"""
Module for managing proportional relationships for Katana resources.
"""

# Default to normalized proportions
_DEFAULT_NODES = 1/3
_DEFAULT_TASKS = 1/3
_DEFAULT_MEMORY = 1/3

PROPORTIONS = {
    "nodes": _DEFAULT_NODES,
    "tasks": _DEFAULT_TASKS,
    "memory": _DEFAULT_MEMORY,
}

def set_proportions(nodes: float, tasks: float, memory: float):
    """
    Sets the proportions for nodes, tasks, and memory.
    Values should be positive and will be normalized to sum to 1.
    """
    if nodes < 0 or tasks < 0 or memory < 0:
        raise ValueError("Proportions must be non-negative.")

    total = nodes + tasks + memory
    if total == 0:
        # Default to equal distribution if all are zero
        PROPORTIONS["nodes"] = 1/3
        PROPORTIONS["tasks"] = 1/3
        PROPORTIONS["memory"] = 1/3
    else:
        PROPORTIONS["nodes"] = nodes / total
        PROPORTIONS["tasks"] = tasks / total
        PROPORTIONS["memory"] = memory / total

def get_proportions():
    """
    Returns the current proportions for nodes, tasks, and memory.
    """
    return PROPORTIONS.copy()

def get_recommendations(total_resources: dict):
    """
    Provides resource distribution recommendations based on current proportions.

    Args:
        total_resources (dict): A dictionary containing the total available
                                resources, e.g., {"nodes": 100, "tasks": 50, "memory_gb": 128}.
                                Expected keys are 'nodes', 'tasks', 'memory_gb'.

    Returns:
        dict: A dictionary with recommended resource allocations.
    """
    recommendations = {}
    proportions = get_proportions()

    if "nodes" in total_resources:
        recommendations["nodes"] = round(total_resources["nodes"] * proportions["nodes"])
    if "tasks" in total_resources:
        recommendations["tasks"] = round(total_resources["tasks"] * proportions["tasks"])
    if "memory_gb" in total_resources:
        # Assuming memory is in GB, recommend in GB
        recommendations["memory_gb"] = round(total_resources["memory_gb"] * proportions["memory"], 2)

    return recommendations
