import click
from katana.tools import doctor as doctor_module

@click.group()
def cli():
    """Katana AI CLI Tool"""
    pass

@cli.command()
@click.option('--auto-fix', is_flag=True, help='Automatically attempt to fix detected issues.')
@click.option('--clear-cache', is_flag=True, help='Clear the HuggingFace cache directory (requires confirmation).')
def doctor(auto_fix, clear_cache):
    """
    Diagnose and fix common environment and dependency issues for Katana.
    """
    doctor_module.run_doctor(auto_fix=auto_fix, clear_cache_flag=clear_cache)

if __name__ == '__main__':
    cli()
