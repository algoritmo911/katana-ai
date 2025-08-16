import collections

# Using a named tuple for a simple, immutable Skill definition.
# In a real system, this would likely be a more complex class.
Skill = collections.namedtuple("Skill", ["name", "description", "func"])


class SkillGraph:
    """
    A simple registry for Katana's skills.

    In a future, more complex implementation, this would be a true graph
    structure, allowing for complex skill chaining and data flow. For now,
    it acts as a simple dictionary-based registry.
    """

    def __init__(self):
        self._skills = {}

    def register_skill(self, skill: Skill):
        """Registers a new skill."""
        if skill.name in self._skills:
            # In a real system, we might want to handle this more gracefully.
            raise ValueError(f"Skill '{skill.name}' is already registered.")
        self._skills[skill.name] = skill
        print(f"Registered skill: {skill.name}")

    def get_skill(self, name: str) -> Skill:
        """Retrieves a skill by its name."""
        skill = self._skills.get(name)
        if not skill:
            raise ValueError(f"Skill '{name}' not found.")
        return skill

    def get_all_skills(self) -> list[Skill]:
        """Returns a list of all registered skills."""
        return list(self._skills.values())
