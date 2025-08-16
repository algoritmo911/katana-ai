import datetime

from katana_ai.skill_graph import Skill, SkillGraph


def echo(*args: str) -> str:
    """A simple skill that returns the arguments it received."""
    if not args:
        return "echo skill called with no arguments."
    return " ".join(args)


def current_time() -> str:
    """A simple skill that returns the current time in UTC."""
    return f"Current UTC time: {datetime.datetime.utcnow().isoformat()}"


def register_basic_skills(graph: SkillGraph):
    """
    Registers all the basic skills into the provided SkillGraph.
    """
    graph.register_skill(
        Skill(
            name="echo",
            description="Returns the arguments it was called with.",
            func=echo,
        )
    )
    graph.register_skill(
        Skill(
            name="current_time",
            description="Returns the current UTC time.",
            func=current_time,
        )
    )
    # A skill to list all available skills
    graph.register_skill(
        Skill(
            name="help",
            description="Lists all available commands.",
            # The function uses a lambda to get access to the graph instance.
            func=lambda: "\n".join(
                [f"- {s.name}: {s.description}" for s in graph.get_all_skills()]
            ),
        )
    )
