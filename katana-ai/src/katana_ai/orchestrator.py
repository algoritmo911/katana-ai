from .skill_graph import SkillGraph


import structlog

class CognitiveOrchestrator:
    """
    The central node for decision-making in the Katana AI.

    It analyzes the user's request, consults the SkillGraph, and executes
    the appropriate skill.
    """

    def __init__(self, skill_graph: SkillGraph, logger=None):
        self._skill_graph = skill_graph
        self.log = logger or structlog.get_logger()

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

        log = self.log.bind(command=command, skill_name=skill_name)
        log.info("command_received")

        try:
            skill = self._skill_graph.get_skill(skill_name)

            # Special handling for skills that take a single string argument
            if skill_name in ["ask"]:
                # Re-join all arguments after the command into a single string
                query_string = " ".join(parts[1:])
                if not query_string:
                    return f"Error: The '{skill_name}' command requires an argument."
                result = skill.func(query_string)
            else:
                # Original behavior for simple commands
                args = parts[1:]
                result = skill.func(*args)

            return str(result)
        except ValueError as e:
            log.error("skill_not_found", error=str(e))
            return f"Error: {e}"
        except TypeError:
            log.error("skill_invalid_arguments")
            return f"Error: Invalid arguments for skill '{skill_name}'."
        except Exception as e:
            log.exception("skill_execution_failed")
            return f"An unexpected error occurred: {e}"
