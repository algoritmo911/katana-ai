# This module contains all the logic for interacting with Kubernetes, Kind, and Helm.
import subprocess
import sys
import os
from rich.console import Console

console = Console()
CLUSTER_NAME = "katana-dev"
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

def check_cluster() -> bool:
    """Checks if the Kind cluster already exists."""
    console.print(f"Checking for existing Kind cluster named '[cyan]{CLUSTER_NAME}[/cyan]'...")
    try:
        # kind might need sudo if docker requires it.
        result = subprocess.run(
            ["sudo", "kind", "get", "clusters"],
            check=True, capture_output=True, text=True
        )
        clusters = result.stdout.strip().split("\n")
        if CLUSTER_NAME in clusters:
            console.print(f"[green]✅ Cluster '{CLUSTER_NAME}' found.[/green]")
            return True
        else:
            console.print(f"[yellow]Cluster '{CLUSTER_NAME}' not found.[/yellow]")
            return False
    except FileNotFoundError:
        console.print("[bold red]Error: 'kind' command not found. Is it installed and in your PATH?[/bold red]")
        return False
    except subprocess.CalledProcessError as e:
        # If `kind get clusters` fails when no clusters exist, it's not a "real" error for us.
        # We can treat it as "cluster not found". The command returns non-zero in this case.
        if "no kind clusters found" in e.stderr.lower():
             console.print(f"[yellow]Cluster '{CLUSTER_NAME}' not found.[/yellow]")
             return False
        console.print(f"[bold red]Error checking for Kind clusters:[/bold red] {e.stderr}")
        return False


def create_cluster() -> bool:
    """Creates a new Kind cluster."""
    console.print(f"Creating new Kind cluster '[cyan]{CLUSTER_NAME}[/cyan]'... This may take a minute.")
    try:
        subprocess.run(
            ["sudo", "kind", "create", "cluster", "--name", CLUSTER_NAME],
            check=True, capture_output=True, text=True
        )
        console.print(f"[green]✅ Successfully created cluster '{CLUSTER_NAME}'.[/green]")
        return True
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        console.print(f"[bold red]Error creating Kind cluster:[/bold red]\n{e.stderr}")
        return False

def load_docker_image(image_name: str) -> bool:
    """Loads a locally built Docker image into the Kind cluster."""
    console.print(f"Loading image '[cyan]{image_name}[/cyan]' into Kind cluster '[cyan]{CLUSTER_NAME}[/cyan]'...")
    try:
        subprocess.run(
            ["sudo", "kind", "load", "docker-image", image_name, "--name", CLUSTER_NAME],
            check=True, capture_output=True, text=True
        )
        console.print(f"[green]✅ Successfully loaded image '{image_name}'.[/green]")
        return True
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        console.print(f"[bold red]Error loading Docker image into Kind:[/bold red]\n{e.stderr}")
        return False

def build_docker_image(image_tag: str) -> bool:
    """Builds the Docker image for the application."""
    console.print(f"Building Docker image '[cyan]{image_tag}[/cyan]'...")
    try:
        # Use subprocess.run and capture output to see errors if they occur
        subprocess.run(
            ["sudo", "docker", "build", "-t", image_tag, "."],
            check=True,
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT
        )
        console.print(f"[green]✅ Successfully built image '{image_tag}'.[/green]")
        return True
    except FileNotFoundError:
        console.print("[bold red]Error: 'docker' command not found.[/bold red]")
        return False
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error building Docker image:[/bold red]\n{e.stderr}")
        return False


def deploy_with_helm(release_name: str, chart_path: str) -> bool:
    """Deploys the application using Helm."""
    console.print(f"Deploying release '[cyan]{release_name}[/cyan]' from chart '[cyan]{chart_path}[/cyan]'...")
    try:
        # Using `helm upgrade --install` is idempotent
        subprocess.run(
            [
                "helm", "upgrade", "--install",
                release_name,
                chart_path,
                "--namespace", "default", # Explicitly targeting the default namespace
                "--wait" # Wait for pods to be ready
            ],
            check=True, capture_output=True, text=True
        )
        console.print(f"[green]✅ Successfully deployed Helm chart '{release_name}'.[/green]")
        return True
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        console.print(f"[bold red]Error deploying with Helm:[/bold red]\n{e.stderr}")
        return False
