import subprocess
import sys
import os
from rich.console import Console

console = Console()
# Define the project root as the directory two levels up from this file's directory
# (<root>/katana-cli/core/runner.py -> <root>)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

def setup_git_hooks():
    """Installs pre-commit hooks."""
    try:
        # First, ensure pre-commit is installed from the root requirements.txt
        # This is a bit of a simplification. A more robust solution might
        # parse requirements.txt or use a shared dependency management.
        console.print("Ensuring pre-commit is installed...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            check=True,
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT
        )


        console.print("Installing git hooks with pre-commit...")
        result = subprocess.run(
            ["pre-commit", "install"],
            check=True,
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT
        )
        console.print(result.stdout)
        console.print("[green]✅ Git hooks installed successfully.[/green]")
        return True
    except FileNotFoundError:
        console.print("[bold red]Error:[/bold red] `pre-commit` command not found. Is it installed and in your PATH?")
        return False
    except subprocess.CalledProcessError as e:
        # Check for the specific "Cowardly refusing" error from pre-commit
        if "Cowardly refusing to install hooks with `core.hooksPath` set" in e.stdout:
            console.print("[yellow]⚠️ Warning: `pre-commit` refused to install hooks due to an existing `core.hooksPath` configuration in the environment.[/yellow]")
            console.print("   This is common in some managed environments. Skipping git hook setup to allow progress.")
            # We return True to allow the rest of the setup to proceed.
            return True
        else:
            # For any other error, we fail as before.
            console.print(f"[bold red]Error during git hook setup (retcode: {e.returncode}):[/bold red]")
            if e.stdout:
                console.print("[bold]--- STDOUT ---[/bold]")
                console.print(e.stdout.strip())
            if e.stderr:
                console.print("[bold]--- STDERR ---[/bold]")
                console.print(e.stderr.strip())
            return False

def start_services():
    """Starts the local development services, e.g., the KatanaBot."""
    try:
        console.print("Attempting to start the KatanaBot application via uvicorn...")

        # Step 1: Install dependencies for the bot
        console.print("Ensuring KatanaBot dependencies are installed...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            check=True,
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT
        )

        # Step 2: Start the uvicorn process and log its output
        console.print("Starting uvicorn server in the background, logging to 'uvicorn.log'...")
        log_file_path = os.path.join(PROJECT_ROOT, "uvicorn.log")

        with open(log_file_path, "wb") as log_file:
            process = subprocess.Popen(
                ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
                stdout=log_file,
                stderr=log_file,
                cwd=PROJECT_ROOT
            )

        console.print(f"[green]✅ KatanaBot service started in the background (PID: {process.pid}).[/green]")
        console.print(f"   - Logs are being written to: [bold cyan]{log_file_path}[/bold cyan]")
        console.print("   - To stop the service, you may need to manually kill the process.")
        return True

    except FileNotFoundError:
        console.print("[bold red]Error:[/bold red] A required command (like `pip` or `uvicorn`) was not found.")
        console.print("       Please ensure Python dependencies from `requirements.txt` are installed.")
        return False
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]An error occurred while installing dependencies:[/bold red]")
        console.print(e.stderr)
        return False
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred while starting uvicorn:[/bold red]\n{e}")
        return False
