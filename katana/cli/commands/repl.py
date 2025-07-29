import click
import asyncio
from rich.console import Console
from rich.prompt import Prompt

@click.command()
@click.pass_context
def repl(ctx):
    """
    Start an interactive REPL session.
    """
    console = Console()
    api_client = ctx.obj.get("api_client")

    if not api_client:
        console.print("Not connected to a Katana core. Please provide a WebSocket endpoint using the --ws-endpoint option or by setting it in the config file.")
        return

    console.print("Welcome to the Katana AI REPL. Type 'exit' to quit.")

    while True:
        try:
            command = Prompt.ask("> ")
            if command == "exit":
                break

            parts = command.split()
            cmd = parts[0]
            args = parts[1:]

            # This is a very basic implementation. A more robust implementation
            # would use a proper command parser.
            if cmd in ["status", "ping", "queue"]:
                result = asyncio.run(api_client.send_command(cmd, {}))
                console.print(result)
            elif cmd in ["cancel", "log", "history"]:
                # This is a simplified implementation for the sake of the example.
                # A real implementation would need to parse the arguments properly.
                console.print("This command is not yet supported in REPL mode.")
            else:
                console.print(f"Unknown command: {cmd}")

        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"Error: {e}")
