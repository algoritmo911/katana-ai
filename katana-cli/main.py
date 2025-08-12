import typer
from rich.console import Console
import sys
import os

# Add the parent directory of 'katana-cli' to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core import system, kubernetes

# --- Configuration ---
APP_NAME = "katanabot"
DOCKER_IMAGE_TAG = f"{APP_NAME}:latest"
HELM_RELEASE_NAME = "katanabot-release"
HELM_CHART_PATH = "./charts/katanabot"
# ---------------------

app = typer.Typer(rich_markup_mode="rich", help="🚀 The CLI for The Forge development environment.")
env_app = typer.Typer(rich_markup_mode="rich", help="Manage the development environment.")
app.add_typer(env_app, name="env")

console = Console()

@env_app.command("up", help="Builds and deploys the full local environment on Kubernetes (Kind).")
def env_up():
    """
    Orchestrates the setup of the complete local development environment using Kind and Helm.
    """
    console.print("🚀 [bold green]Starting The Forge Environment Setup (Stage 2: Kubernetes)...[/bold green]")

    # Step 1: System Dependencies Check
    console.print("\n[cyan]Step 1: Checking System Dependencies...[/cyan]")
    if not system.check_dependencies():
        console.print("\n[bold red]Error:[/bold red] System dependencies check failed. Please install missing tools.")
        raise typer.Exit(code=1)
    console.print("[green]✅ All system dependencies found.[/green]")

    # Step 2: Build Docker Image
    console.print("\n[cyan]Step 2: Building Application Docker Image...[/cyan]")
    if not kubernetes.build_docker_image(DOCKER_IMAGE_TAG):
        raise typer.Exit(code=1)

    # Step 3: Ensure Kind Cluster is Running
    console.print("\n[cyan]Step 3: Verifying Kubernetes Cluster (Kind)...[/cyan]")
    if not kubernetes.check_cluster():
        if not kubernetes.create_cluster():
            raise typer.Exit(code=1)

    # Step 4: Load Docker Image into Kind
    console.print("\n[cyan]Step 4: Loading Docker Image into Kind...[/cyan]")
    if not kubernetes.load_docker_image(DOCKER_IMAGE_TAG):
        raise typer.Exit(code=1)

    # Step 5: Deploy with Helm
    console.print("\n[cyan]Step 5: Deploying Application with Helm...[/cyan]")
    if not kubernetes.deploy_with_helm(HELM_RELEASE_NAME, HELM_CHART_PATH):
        raise typer.Exit(code=1)

    console.print("\n🎉 [bold green]Forge environment is up and running on Kubernetes![/bold green]")
    console.print("   - Use 'kubectl get pods' to see the running application.")
    console.print("   - Check the Helm release status with 'helm status katanabot-release'.")
    console.print("   - To access the service, follow the instructions in the Helm chart's NOTES.")

if __name__ == "__main__":
    app()
