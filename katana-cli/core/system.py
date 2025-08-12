# This file will contain system-related functions, like dependency checks.
import shutil
from rich.console import Console

console = Console()

def check_dependencies():
    """Checks for required system dependencies for Stage 2."""
    console.print("Checking for Docker, kubectl, kind, and helm...")

    dependencies = {
        "docker": "This is required to build container images.",
        "kubectl": "This is required to interact with the Kubernetes cluster.",
        "kind": "This is required to create a local Kubernetes cluster.",
        "helm": "This is required to deploy applications into the cluster."
    }

    all_found = True
    for dep, reason in dependencies.items():
        if shutil.which(dep):
            console.print(f"[green]✅ {dep} found.[/green]")
        else:
            console.print(f"[bold red]❌ {dep} not found.[/bold red] {reason}")
            all_found = False

    return all_found
