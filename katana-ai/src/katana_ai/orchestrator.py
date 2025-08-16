from .skill_graph import SkillGraph


class CognitiveOrchestrator:
    """
    The central node for decision-making in the Katana AI.

    It analyzes the user's request, consults the SkillGraph, and executes
    the appropriate skill.
    """

    def __init__(self, skill_graph: SkillGraph):
        self._skill_graph = skill_graph

    def execute_command(self, command: str) -> str:
        """
        Parses and executes a user command.

        Args:
            command: The raw command string from the user.

        Returns:
            A string representing the result of the command execution.
        """
        if not command:
            return "Error: Empty command."

        parts = command.strip().split()
        skill_name = parts[0]
        args = parts[1:]

        try:
            skill = self._skill_graph.get_skill(skill_name)
            # Execute the skill's function with the provided arguments.
            result = skill.func(*args)
            return str(result)
        except ValueError as e:
            # Skill not found
            return f"Error: {e}"
        except TypeError:
            # Mismatched arguments
            return f"Error: Invalid arguments for skill '{skill_name}'."
        except Exception as e:
            # Catch any other exceptions during skill execution.
            return f"An unexpected error occurred: {e}"
