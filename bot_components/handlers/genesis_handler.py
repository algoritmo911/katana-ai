"""
This module contains the handler for the /genesis command, which automates
the creation of new agent boilerplate code.
"""
import yaml
from pathlib import Path
import telebot
import subprocess

# This is a simplified, hardcoded simulation of an LLM call.
# In a real system, this would involve a call to a service like OpenAI,
# passing the architect prompt and the user's YAML blueprint.
def _call_llm_simulation(prompt: str, blueprint: dict) -> str:
    """
    Simulates a call to a large language model to generate agent code.
    """
    agent_name = blueprint.get("name", "DefaultAgent")
    # Convert "Example Agent" to "ExampleAgent"
    class_name = "".join(word.capitalize() for word in agent_name.split())
    purpose = blueprint.get("purpose", "No purpose provided.")
    dependencies = blueprint.get("dependencies", [])
    methods = blueprint.get("methods", [])

    imports = "\n".join(f"import {dep}" for dep in dependencies)

    method_definitions = []
    for method in methods:
        method_name = method.get("name")
        inputs = method.get("inputs", {})
        # A real implementation would need to infer types more robustly.
        args = ", ".join(f"{name}: str" for name in inputs.keys())
        # For simulation, we'll assume a string return type.
        method_code = f"""
    def {method_name}(self, {args}) -> str:
        \"\"\"
        {method.get("description", "")}

        Args:
            {', '.join(inputs.keys())}

        Returns:
            str: A placeholder return value.
        \"\"\"
        pass
"""
        method_definitions.append(method_code)

    method_definitions_str = "\n".join(method_definitions)

    # This is a simplified template. The real LLM would generate this more dynamically.
    return f'''
"""
{purpose}
"""
{imports}
from typing import Dict, Any

class {class_name}:
    """{purpose}"""

    def __init__(self):
        """Initializes the {class_name}."""
        pass

{method_definitions_str}
'''


def handle_genesis(command_data: dict, message: telebot.types.Message, bot: telebot.TeleBot):
    """
    Handles the /genesis command by generating a new agent file from a YAML blueprint.
    """
    try:
        # The YAML content is expected to be in the 'blueprint' argument.
        blueprint_yaml = command_data.get("args", {}).get("blueprint")
        if not blueprint_yaml:
            bot.reply_to(message, "Error: The 'blueprint' argument is missing in the command args.")
            return

        blueprint = yaml.safe_load(blueprint_yaml)

        # In a real implementation, we would read the prompt from the .md file.
        # For this simulation, we'll just pass a placeholder string.
        with open("prompts/genesis_architect_prompt.md", "r", encoding="utf-8") as f:
            architect_prompt = f.read()

        generated_code = _call_llm_simulation(architect_prompt, blueprint)

        agent_name = blueprint.get("name", "unnamed_agent")
        agent_filename = f"{agent_name.lower().replace(' ', '_')}.py"

        # Ensure the agents directory exists
        agents_dir = Path("src/agents")
        agents_dir.mkdir(parents=True, exist_ok=True)

        agent_file_path = agents_dir / agent_filename

        with open(agent_file_path, "w", encoding="utf-8") as f:
            f.write(generated_code.strip())

        # Layer 5: Quality Control
        qc_results = ""
        try:
            # Run black for formatting. We don't use check=True as it returns non-zero on reformatting.
            black_result = subprocess.run(
                ["black", str(agent_file_path)],
                capture_output=True,
                text=True,
            )
            if black_result.returncode == 0:
                qc_results += "✅ `black` formatting successful (no changes needed).\n"
            else:
                qc_results += "✅ `black` formatting successful (reformatted file).\n"

            # Run flake8 for linting
            flake8_result = subprocess.run(
                ["flake8", str(agent_file_path)],
                capture_output=True,
                text=True,
            )
            if flake8_result.returncode == 0:
                qc_results += "✅ `flake8` linting successful (no issues found)."
            else:
                qc_results += f"⚠️ `flake8` found issues:\n```\n{flake8_result.stdout}\n```"

        except FileNotFoundError as e:
            # This catches errors if black or flake8 are not installed
            qc_results += f"⚠️ QC tool not found: {e.filename}. Please ensure 'black' and 'flake8' are installed."
        except Exception as e:
            qc_results += f"An unexpected error occurred during QC: {e}"


        reply_msg = f"✅ Genesis complete. New agent created at: `{agent_file_path}`\n\n**Quality Control Results:**\n{qc_results}"
        bot.reply_to(message, reply_msg, parse_mode="Markdown")

    except yaml.YAMLError as e:
        bot.reply_to(message, f"Error parsing YAML blueprint: {e}")
    except Exception as e:
        bot.reply_to(message, f"An unexpected error occurred: {e}")
