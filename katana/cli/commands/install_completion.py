import click
import click_completion

@click.command()
@click.option('--append/--overwrite', help='Append the completion code to the file', default=None)
@click.option('-i', '--case-insensitive/--no-case-insensitive', help='Case-insensitive completion')
@click.argument('shell', required=False, type=click_completion.DocumentedChoice(click_completion.core.shells))
def install_completion(shell, append, case_insensitive):
    """Install the command line tool's completion for your shell"""
    # The actual installation is handled by the click_completion library.
    # This command is just a placeholder to make the --install-completion option work.
    pass
