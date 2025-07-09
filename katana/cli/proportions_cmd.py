import argparse
from katana.proportions import set_proportions, get_proportions, get_recommendations
from katana.decorators.trace_command import trace_command

@trace_command
def set_proportions_command(args):
    """
    CLI command to set resource proportions.
    """
    try:
        set_proportions(args.nodes, args.tasks, args.memory)
        print("Proportions updated successfully.")
        current_proportions = get_proportions()
        print(f"Current normalized proportions: Nodes: {current_proportions['nodes']:.2f}, Tasks: {current_proportions['tasks']:.2f}, Memory: {current_proportions['memory']:.2f}")
    except ValueError as e:
        print(f"Error: {e}")

@trace_command
def get_proportions_command(args):
    """
    CLI command to get current resource proportions.
    """
    proportions = get_proportions()
    print(f"Current proportions: Nodes: {proportions['nodes']:.2f}, Tasks: {proportions['tasks']:.2f}, Memory: {proportions['memory']:.2f}")

@trace_command
def recommend_resources_command(args):
    """
    CLI command to get resource recommendations.
    """
    # These are example total resources. In a real scenario, these might come from a config file or system scan.
    total_resources = {
        "nodes": args.total_nodes,
        "tasks": args.total_tasks,
        "memory_gb": args.total_memory_gb
    }

    # Ensure proportions are set if the user provides them, otherwise use existing
    if args.nodes is not None and args.tasks is not None and args.memory is not None:
        try:
            set_proportions(args.nodes, args.tasks, args.memory)
            print("Using provided proportions for this recommendation.")
        except ValueError as e:
            print(f"Error setting proportions: {e}")
            return

    recommendations = get_recommendations(total_resources)
    current_proportions = get_proportions()

    print("Based on current proportions:")
    print(f"  Nodes: {current_proportions['nodes']:.2f}")
    print(f"  Tasks: {current_proportions['tasks']:.2f}")
    print(f"  Memory: {current_proportions['memory']:.2f}")
    print("\nRecommended resource allocation:")
    if "nodes" in recommendations:
        print(f"  Recommended Nodes: {recommendations['nodes']} (out of {total_resources['nodes']} total)")
    if "tasks" in recommendations:
        print(f"  Recommended Tasks: {recommendations['tasks']} (out of {total_resources['tasks']} total)")
    if "memory_gb" in recommendations:
        print(f"  Recommended Memory: {recommendations['memory_gb']:.2f} GB (out of {total_resources['memory_gb']} GB total)")

def register_proportions_commands(subparsers):
    """
    Registers proportions subcommands with the main CLI parser.
    """
    proportions_parser = subparsers.add_parser("proportions", help="Manage resource proportions and get recommendations.")
    proportions_subparsers = proportions_parser.add_subparsers(title="Commands", dest="proportions_command", required=True)

    # proportions set
    set_parser = proportions_subparsers.add_parser("set", help="Set resource proportions (e.g., nodes, tasks, memory).")
    set_parser.add_argument("--nodes", type=float, required=True, help="Proportion for nodes (e.g., 0.5).")
    set_parser.add_argument("--tasks", type=float, required=True, help="Proportion for tasks (e.g., 0.3).")
    set_parser.add_argument("--memory", type=float, required=True, help="Proportion for memory (e.g., 0.2).")
    set_parser.set_defaults(func=set_proportions_command)

    # proportions get
    get_parser = proportions_subparsers.add_parser("get", help="Get current resource proportions.")
    get_parser.set_defaults(func=get_proportions_command)

    # proportions recommend
    recommend_parser = proportions_subparsers.add_parser("recommend", help="Get resource recommendations based on proportions.")
    recommend_parser.add_argument("--total-nodes", type=int, default=100, help="Total available nodes.")
    recommend_parser.add_argument("--total-tasks", type=int, default=200, help="Total available tasks capacity.")
    recommend_parser.add_argument("--total-memory-gb", type=float, default=256.0, help="Total available memory in GB.")
    # Optional arguments to override current proportions for this specific recommendation
    recommend_parser.add_argument("--nodes", type=float, help="Override node proportion for this recommendation.")
    recommend_parser.add_argument("--tasks", type=float, help="Override task proportion for this recommendation.")
    recommend_parser.add_argument("--memory", type=float, help="Override memory proportion for this recommendation.")
    recommend_parser.set_defaults(func=recommend_resources_command)
