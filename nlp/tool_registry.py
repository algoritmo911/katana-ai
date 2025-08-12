import os
import importlib
import inspect
from pathlib import Path
from typing import Type, Dict, List, Any
from pydantic import BaseModel, Field

class ToolParameters(BaseModel):
    """Base model for tool parameters. All tool parameter models should inherit from this."""
    pass

class ToolContract(BaseModel):
    """
    Defines the contract for a tool that the AI can use.
    It includes the tool's name, a description for the LLM to understand its purpose,
    and a Pydantic model defining the parameters (slots) the tool requires.
    """
    name: str = Field(..., description="The unique name of the function to be called.")
    description: str = Field(..., description="A detailed, natural language description of what the tool does.")
    parameters: Type[ToolParameters] = Field(..., description="A Pydantic model defining the arguments for the tool.")

    class Config:
        arbitrary_types_allowed = True


class ToolRegistry:
    """
    A registry that discovers, loads, and stores all available tool contracts.
    """
    def __init__(self, tools_directory: str = "nlp/tools"):
        self.tools_directory = Path(tools_directory)
        self._tools: Dict[str, ToolContract] = {}
        self.load_tools()

    def load_tools(self):
        """
        Scans the specified tools directory, imports Python modules, and registers
        any ToolContract instances found within them.
        """
        if not self.tools_directory.is_dir():
            print(f"Warning: Tools directory '{self.tools_directory}' not found. No tools will be loaded.")
            return

        for file_path in self.tools_directory.glob("*.py"):
            if file_path.name.startswith("_"):
                continue

            # Correctly construct the module path for importlib
            module_name = f"nlp.{self.tools_directory.name}.{file_path.stem}"
            try:
                module = importlib.import_module(module_name)
                for _, obj in inspect.getmembers(module):
                    if isinstance(obj, ToolContract):
                        if obj.name in self._tools:
                            print(f"Warning: Duplicate tool name '{obj.name}' found. Overwriting.")
                        self._tools[obj.name] = obj
                        print(f"Successfully registered tool: '{obj.name}'")
            except ImportError as e:
                print(f"Error importing tool module {module_name}: {e}")

    def get_tool(self, name: str) -> ToolContract | None:
        """Retrieves a tool contract by its name."""
        return self._tools.get(name)

    def get_all_tools(self) -> List[ToolContract]:
        """Returns a list of all registered tool contracts."""
        return list(self._tools.values())

    def get_tool_schemas_for_llm(self) -> List[Dict[str, Any]]:
        """
        Returns a list of simplified tool schemas suitable for inclusion in an LLM prompt.
        """
        schemas = []
        for tool in self.get_all_tools():
            schema = {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters.model_json_schema()
            }
            schemas.append(schema)
        return schemas

# Example of a global registry instance if needed, or it can be instantiated in the main app
# tool_registry = ToolRegistry()
