import click
import asyncio
from katana.orchestrator.parser import parse_scenario
from katana.orchestrator.runner import run_scenario
from katana.orchestrator.context import Context

@click.command()
@click.argument("scenario_file")
@click.option("--dry-run", is_flag=True, help="Don't actually run the steps.")
@click.option("--visualize", is_flag=True, help="Visualize the scenario.")
@click.option("--var", multiple=True, help="Set a variable for the scenario.")
def orchestrate(scenario_file, dry_run, visualize, var):
    """
    Run a scenario from a YAML file.
    """
    context = Context()
    for v in var:
        key, value = v.split("=", 1)
        context.set_env(key, value)

    scenario = parse_scenario(scenario_file, context)

    if visualize:
        # In a real implementation, this would generate a visualization of the scenario.
        console.print("Visualization is not yet implemented.")
        return

    if dry_run:
        console.print("Dry run mode. The following steps would be executed:")
        for step in scenario.get("steps", []):
            console.print(step)
        return

    asyncio.run(run_scenario(scenario, context))
