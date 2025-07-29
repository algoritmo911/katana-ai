import click
from rich.console import Console

from .commands import *

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
main.add_command(orchestrate)
main.add_command(install_completion)

if __name__ == "__main__":
    main()
