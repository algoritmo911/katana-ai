# This file makes katana.logging a Python package.

from .telemetry_logger import get_command_logger

__all__ = ['get_command_logger']
