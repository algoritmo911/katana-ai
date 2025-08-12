import click
import redis
import sys
from pathlib import Path

# This allows the CLI to be run from the root directory and find the 'katana' package
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Redis keys for mission control
MISSION_GOAL_KEY = "wanderer:mission:goal"
MISSION_SEED_URL_KEY = "wanderer:mission:seed_url"
MISSION_STATUS_KEY = "wanderer:mission:status"
FRONTIER_QUEUE_KEY = "wanderer_frontier"

# Connect to Redis
try:
    redis_client = redis.Redis(decode_responses=True)
    # Check connection
    redis_client.ping()
except redis.exceptions.ConnectionError as e:
    # This will be printed if the file is imported, which is not ideal,
    # but for a simple CLI it's a starting point.
    print(f"Warning: Could not connect to Redis. CLI commands may fail. Error: {e}")
    redis_client = None

@click.group()
def wanderer():
    """Commands to control the Wanderer agent."""
    pass

@wanderer.command()
@click.option('--mission', required=True, help='The goal of the exploration mission.')
@click.option('--seed_url', required=True, help='The starting URL for the mission.')
def start(mission, seed_url):
    """Starts a new Wanderer exploration mission."""
    if not redis_client:
        click.echo(click.style("Error: Redis connection not available.", fg='red'))
        return

    click.echo("Received 'start' command...")
    try:
        status = redis_client.get(MISSION_STATUS_KEY)
        if status == 'RUNNING':
            click.echo(click.style("Error: A mission is already in progress.", fg='red'))
            return

        click.echo(f"  - Setting mission goal: {mission}")
        redis_client.set(MISSION_GOAL_KEY, mission)

        click.echo(f"  - Setting seed URL: {seed_url}")
        redis_client.set(MISSION_SEED_URL_KEY, seed_url)

        click.echo("  - Clearing old frontier queue and adding seed URL.")
        redis_client.delete(FRONTIER_QUEUE_KEY)
        redis_client.zadd(FRONTIER_QUEUE_KEY, {seed_url: 1.0})

        click.echo("  - Setting mission status to RUNNING.")
        redis_client.set(MISSION_STATUS_KEY, "RUNNING")

        click.echo(click.style("\nMission started successfully!", fg='green'))
        click.echo("A WandererAgent worker process can now be started to execute the mission.")

    except redis.exceptions.ConnectionError as e:
        click.echo(click.style(f"Error communicating with Redis: {e}", fg='red'))

@wanderer.command()
def status():
    """Checks the status of the current Wanderer mission."""
    if not redis_client:
        click.echo(click.style("Error: Redis connection not available.", fg='red'))
        return

    click.echo("Received 'status' command...")
    try:
        status = redis_client.get(MISSION_STATUS_KEY)
        goal = redis_client.get(MISSION_GOAL_KEY)

        if not status or status != 'RUNNING':
            click.echo("No active mission found.")
            return

        queue_size = redis_client.zcard(FRONTIER_QUEUE_KEY)

        click.echo(click.style("--- Wanderer Mission Status ---", bold=True))
        click.echo(f"  - Status: {click.style(status, fg='green')}")
        click.echo(f"  - Goal: {goal}")
        click.echo(f"  - URLs in Frontier Queue: {queue_size}")

    except redis.exceptions.ConnectionError as e:
        click.echo(click.style(f"Error communicating with Redis: {e}", fg='red'))

@wanderer.command()
def stop():
    """Stops the current Wanderer mission."""
    if not redis_client:
        click.echo(click.style("Error: Redis connection not available.", fg='red'))
        return

    click.echo("Received 'stop' command...")
    try:
        redis_client.set(MISSION_STATUS_KEY, "STOPPING")
        click.echo(click.style("Stop signal sent. Agent will halt after its current task.", fg='yellow'))
    except redis.exceptions.ConnectionError as e:
        click.echo(click.style(f"Error communicating with Redis: {e}", fg='red'))

# This file now only defines the 'wanderer' command group.
# It should be imported and added to the main cli object in main.py.
