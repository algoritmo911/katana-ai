import sys
import logging
from .agent import KatanaAgent
from .executor import ShellExecutor, CommandResult
from .utils import get_current_time

# A set of commands that are treated as shell commands to be executed locally.
# This list can be expanded.
SHELL_COMMANDS = {
    'ls', 'pwd', 'df', 'ps', 'whoami', 'echo', 'cd', 'cat', 'grep', 'find'
}

def is_shell_command(command: str) -> bool:
    """Check if the given command is a shell command."""
    return command.strip().split()[0] in SHELL_COMMANDS

def main():
    """
    The main entry point for the Katana Terminal Agent CLI.
    """
    print("🧠 Katana Terminal Agent активен.")

    try:
        agent = KatanaAgent()
        executor = ShellExecutor()
    except ValueError as e:
        logging.error(e)
        sys.exit(1)

    while True:
        try:
            prompt = input("💬 Введи команду: ")

            if not prompt.strip():
                continue

            if prompt.strip().lower() in ['exit', 'quit']:
                print("👋 Катана уходит в тень. До встречи.")
                break

            if prompt.strip().lower() == 'time':
                print(f"⏰ Сейчас: {get_current_time()}. Солнечный день для апгрейда системы.")
                continue

            if is_shell_command(prompt):
                result: CommandResult = executor.execute(prompt)

                # Prepare output for the agent and for printing
                output = ""
                if result.stdout:
                    output += f"STDOUT:\n{result.stdout}\n"
                if result.stderr:
                    output += f"STDERR:\n{result.stderr}\n"
                if not output:
                    output = "Команда не дала вывода."

                print(f"💻 Результат выполнения:\n{output}")

                # Get a comment from the agent
                agent_response = agent.get_response(prompt, output)
                print(f"\n🗡️ Катана: {agent_response}")

            else:
                # If it's not a shell command, let the agent handle it directly
                agent_response = agent.get_response(prompt)
                print(f"🗡️ Катана: {agent_response}")

        except KeyboardInterrupt:
            print("\n👋 Катана уходит в тень. До встречи.")
            break
        except Exception as e:
            logging.error(f"An unexpected error occurred in the CLI loop: {e}")
            print(f"💥 Произошла системная ошибка: {e}")

if __name__ == "__main__":
    main()
