# katana_core/agent.py - Entry point for KatanaCore CLI

# To run this from outside katana_core (e.g., from project root /app):
# python -m katana_core.agent
# (This requires katana_core's parent, i.e. /app, to be in PYTHONPATH,
# and katana_core/__init__.py to exist)

# If running from within katana_core/ (e.g. cd katana_core; python agent.py):
# from katana import KatanaCore # Old import
from katana.core.cli_agent.katana import KatanaCore # Corrected absolute import
# Pathlib and other imports are handled by katana.py if needed by KatanaCore itself.

import logging
from katana.logging_config import setup_logging, get_logger # This should be correct if run with /app in PYTHONPATH

logger = get_logger(__name__)

def main():
    setup_logging(log_level=logging.INFO) # This setup is global for the logger instance

    agent_init_context = {'user_id': 'cli_agent_system', 'chat_id': 'agent_lifecycle', 'message_id': 'agent_initializing'}
    logger.info("Initializing Katana Core Agent...", extra=agent_init_context)

    # KatanaCore's core_dir_path_str defaults to ".", which means it expects
    # commands.json, etc., in the Current Working Directory from where agent.py is run.
    # If agent.py is in /app/katana_core/cli_agent/ and run from there,
    # then "." is /app/katana_core/cli_agent/, which is correct if data files are there.
    # KatanaCore itself (in katana.py) will log its own initialization with its own context.
    katana_instance = KatanaCore(core_dir_path_str=".") # Assumes data files are in CWD or structure handled by KatanaCore

    katana_instance.run() # KatanaCore.run() has its own detailed logging

    agent_term_context = {'user_id': 'cli_agent_system', 'chat_id': 'agent_lifecycle', 'message_id': 'agent_terminated'}
    logger.info("Katana Core Agent terminated.", extra=agent_term_context)

if __name__ == "__main__":
    # This structure allows the script to be run directly.
    # For KatanaCore to find its files correctly when agent.py is run,
    # the CWD should be the katana_core directory itself.
    # Example:
    # cd katana_core
    # python agent.py
    # OR, if katana_core is in PYTHONPATH and you run `python -m katana_core.agent` from parent dir,
    # KatanaCore(core_dir_path_str=".") might be relative to where python -m is invoked from.
    # It's often safer for KatanaCore to resolve paths relative to its *own* file location
    # if it's meant to be a self-contained package with data.
    # However, the current KatanaCore takes core_dir_path_str which defaults to "." (CWD).
    # The __init__ in KatanaCore resolves it: self.core_dir = Path(core_dir_path_str).resolve()
    main()
