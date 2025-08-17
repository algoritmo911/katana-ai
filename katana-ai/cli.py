import sys
import os
import structlog
import uuid

from katana_ai.logging_config import configure_logging

# Configure logging as the first step
configure_logging()
log = structlog.get_logger()

# Add the 'src' directory to the Python path to allow for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from katana_ai.skill_graph import SkillGraph
from katana_ai.orchestrator import CognitiveOrchestrator
from katana_ai.skills.skill_registrar import register_all_skills


def main():
    """
    Main function to run the Katana AI command-line interface.
    """
    log.info("katana_cli_initializing")

    # 1. Create the skill graph
    skill_graph = SkillGraph()

    # 2. Register all the skills
    register_all_skills(skill_graph)

    # 3. Create the orchestrator
    orchestrator = CognitiveOrchestrator(skill_graph, logger=log)

    log.info("katana_cli_ready")
    print("\nKatana AI CLI is ready. Type 'help' for a list of commands.")
    print("Type 'exit' or 'quit' to end the session.")

    while True:
        try:
            # Generate a unique trace ID for each command execution
            trace_id = str(uuid.uuid4())
            structlog.contextvars.bind_contextvars(trace_id=trace_id)

            command = input("\n> ")
            if command.lower() in ["exit", "quit"]:
                log.info("katana_cli_shutdown")
                print("Shutting down Katana AI. Goodbye.")
                break

            result = orchestrator.execute_command(command)
            print(result)

        except KeyboardInterrupt:
            log.info("katana_cli_shutdown_interrupt")
            print("\nShutting down Katana AI. Goodbye.")
            break
        except Exception as e:
            log.exception("katana_cli_critical_error")
        finally:
            # Clear context vars for the next request
            structlog.contextvars.clear_contextvars()


if __name__ == "__main__":
    main()
