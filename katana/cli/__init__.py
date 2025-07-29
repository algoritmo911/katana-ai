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

from katana.core.auth import get_auth_token

@click.group()
@click.option("--auth-token", help="Authentication token.")
@click.pass_context
def main(ctx, auth_token):
    """
    Katana AI CLI. The ultimate tool for managing your AI assistant.
    """
    ctx.ensure_object(dict)
    if not auth_token:
        auth_token = get_auth_token()
    ctx.obj['auth_token'] = auth_token

main.add_command(status)
main.add_command(cancel)
main.add_command(flush)
main.add_command(log)
main.add_command(history)
main.add_command(ping)
main.add_command(queue)
main.add_command(config)

if __name__ == "__main__":
    main()
