# katana/version.py

# TODO: Read these values from .env or pyproject.toml
__version__ = "0.1.0"
__commit__ = "initial"

def get_version():
    """Returns the current version and commit of Katana."""
    return f"Katana v{__version__} (commit: {__commit__})"
