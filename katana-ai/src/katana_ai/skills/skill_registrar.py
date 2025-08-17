from .basic_skills import register_basic_skills
from .memory_skill import QueryMemorySkill
from katana_ai.skill_graph import Skill, SkillGraph


def register_all_skills(graph: SkillGraph):
    """
    Registers all available skills in the system.
    """
    # Register the simple, stateless skills
    register_basic_skills(graph)

    # Initialize and register the more complex, stateful skills
    # In a real app, a logger would be passed from a central app context
    memory_skill_instance = QueryMemorySkill()

    # The 'ask' skill is the public-facing command for the memory query
    graph.register_skill(
        Skill(
            name="ask",
            description="Asks a question to Katana's long-term memory. Usage: ask <your question>",
            func=memory_skill_instance.execute
        )
    )
