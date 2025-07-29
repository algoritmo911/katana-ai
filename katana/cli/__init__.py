import click
from rich.console import Console

from .status import status
from .cancel import cancel
from .flush import flush
from .log import log
from .history import history
from .ping import ping
from .queue import queue
from .config import config
from .repl import repl
from .run import run
from .results import results

from katana.core.auth import get_auth_token

import click_completion
click_completion.init()
import nest_asyncio
nest_asyncio.apply()
import asyncio
from katana.core.api_client import KatanaApiClient
from katana.core.cli_logic.config import get_config
from katana.core.auth import get_auth_token

@click.group()
@click.option("--auth-token", help="Authentication token.")
@click.option("--ws-endpoint", help="WebSocket endpoint.")
@click.pass_context
def main(ctx, auth_token, ws_endpoint):
    """
    Katana AI CLI. The ultimate tool for managing your AI assistant.
    """
    # The --install-completion option is handled by click_completion
    # and the program exits after printing the completion script.
    pass

@main.command()
@click.option('--append/--overwrite', help='Append the completion code to the file', default=None)
@click.option('-i', '--case-insensitive/--no-case-insensitive', help='Case-insensitive completion')
@click.argument('shell', required=False, type=click_completion.DocumentedChoice(click_completion.core.shells))
def install_completion(shell, append, case_insensitive):
    """Install the command line tool's completion for your shell"""
    # The actual installation is handled by the click_completion library.
    # This command is just a placeholder to make the --install-completion option work.
    pass
    ctx.ensure_object(dict)
    config = get_config()

    if not auth_token:
        auth_token = get_auth_token()
    if not ws_endpoint:
        ws_endpoint = config.get("ws_endpoint")

    ctx.obj['auth_token'] = auth_token
    ctx.obj['ws_endpoint'] = ws_endpoint
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    ctx.obj['api_client'] = KatanaApiClient(ws_endpoint, auth_token, loop=loop) if ws_endpoint else None

main.add_command(status)
main.add_command(cancel)
main.add_command(flush)
main.add_command(log)
main.add_command(history)
main.add_command(ping)
main.add_command(queue)
main.add_command(config)
main.add_command(repl)
main.add_command(run)
main.add_command(results)

if __name__ == "__main__":
    main()
