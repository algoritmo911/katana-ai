import sys
import os

# Add the 'src' directory to the Python path to allow for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from katana_ai.skill_graph import SkillGraph
from katana_ai.orchestrator import CognitiveOrchestrator
from katana_ai.skills.basic_skills import register_basic_skills


def main():
    """
    Main function to run the Katana AI command-line interface.
    """
    print("Initializing Katana AI...")

    # 1. Create the skill graph
    skill_graph = SkillGraph()

    # 2. Register all the skills
    register_basic_skills(skill_graph)

    # 3. Create the orchestrator
    orchestrator = CognitiveOrchestrator(skill_graph)

    print("\nKatana AI CLI is ready. Type 'help' for a list of commands.")
    print("Type 'exit' or 'quit' to end the session.")

    while True:
        try:
            command = input("\n> ")
            if command.lower() in ["exit", "quit"]:
                print("Shutting down Katana AI. Goodbye.")
                break

            result = orchestrator.execute_command(command)
            print(result)

        except KeyboardInterrupt:
            print("\nShutting down Katana AI. Goodbye.")
            break
        except Exception as e:
            print(f"A critical error occurred: {e}")


if __name__ == "__main__":
    main()
