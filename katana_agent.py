import logging
from typing import Optional, List, Callable, Dict, Any

from katana.memory.core import MemoryCore

# It's good practice to get a logger specific to the module
logger = logging.getLogger('katana.agent') # Child logger of 'katana'

class KatanaAgent:
    """
    A general-purpose agent that can be configured with a specific role and a set of tools.
    """
    def __init__(self, name: str = "DefaultAgent", role: str = "Generic Agent", tools: Optional[List[Callable]] = None, memory: Optional[MemoryCore] = None):
        """
        Initializes the KatanaAgent.

        Args:
            name: The name of the agent.
            role: A string describing the agent's specialization (e.g., "Price Analyst").
            tools: A list of functions or tools the agent can use.
            memory: An optional MemoryCore instance for long-term memory.
        """
        self.name = name
        self.role = role
        self.tools = tools if tools is not None else []
        self.memory = memory

        logger.info("KatanaAgent '%s' initialized with role: '%s'.", self.name, self.role)
        if self.memory:
            logger.info("Agent '%s' is memory-enabled.", self.name)
        if self.tools:
            tool_names = [tool.__name__ for tool in self.tools]
            logger.info("Agent '%s' has access to tools: %s", self.name, tool_names)

    def execute(self, task: Dict[str, Any]) -> Any:
        """
        Executes a given task.

        The agent will attempt to find a suitable tool to accomplish the task.
        For this refactored version, the logic is simple: if a tool matches the task's
        'action', it will be executed.

        Args:
            task: A dictionary describing the task. Expected to have an 'action' key
                  and other parameters needed by the tool.

        Returns:
            The result of the tool execution, or an error message if no suitable tool is found.
        """
        action = task.get("action")
        logger.debug("Agent '%s' attempting to perform action: %s", self.name, action)

        if not action:
            logger.error("No action specified in the task for agent '%s'.", self.name)
            return {"error": "No action specified in task."}

        # Find a tool that matches the action
        for tool in self.tools:
            if tool.__name__ == action:
                try:
                    # Pass the task parameters to the tool, excluding the 'action' key
                    params = {k: v for k, v in task.items() if k != 'action'}
                    result = tool(**params)
                    logger.info("Agent '%s' successfully executed action '%s'.", self.name, action)
                    return result
                except Exception as e:
                    logger.error("Error executing tool '%s' for agent '%s': %s", action, self.name, e, exc_info=True)
                    return {"error": f"An error occurred during {action}: {e}"}

        logger.warning("Agent '%s' has no tool to perform action: %s", self.name, action)
        return {"error": f"Agent '{self.name}' cannot perform action '{action}'."}

    def report_status(self):
        logger.info("Agent '%s' (Role: %s) reporting status: All systems nominal.", self.name, self.role)
