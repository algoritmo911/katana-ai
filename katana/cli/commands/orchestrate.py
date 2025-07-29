import click
import asyncio
from katana.orchestrator.parser import parse_scenario
from katana.orchestrator.runner import run_scenario
from katana.orchestrator.context import Context

@click.command()
@click.argument("scenario_file")
def orchestrate(scenario_file):
    """
    Run a scenario from a YAML file.
    """
    steps = parse_scenario(scenario_file)
    context = Context()
    asyncio.run(run_scenario(steps, context))
