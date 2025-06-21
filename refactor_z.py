# refactor_z.py

import os
import shutil
import json
from datetime import datetime # Not used in this version, but can be kept for future use
from katana.logging_config import setup_logging, get_logger

logger = get_logger(__name__)

BASE = "alg911/catana-ai"
DIR_STRUCTURE = [
    "commands", "logs", "status", "modules", "tests", "logs/archive", "processed"
]
FILES = {
    "commands/katana.commands.json": [], # Initialize as empty JSON list
    "status/agent_status.json": {"status": "idle", "timestamp": ""}, # Default status
    "logs/katana_events.log": "", # Empty log file
    "modules/__init__.py": "# Plugin module loader\n",
    "__init__.py": "# alg911/catana-ai package marker\n",
    "tests/__init__.py": "# Tests package marker\n",
    "processed/__init__.py": "# Processed commands archive\n", # Make it a package for potential future importability
    "commands/__init__.py": "# Commands package\n",
    "logs/__init__.py": "# Logs package\n",
    "status/__init__.py": "# Status package\n"

}
MODULE_TEMPLATES = {
    "modules/mind_clearing.py": "def run(**kwargs):\n    print('🧠 Mind cleared by refactor_z.py placeholder.')\n    return {'status':'success', 'message':'Mind cleared (placeholder)'}\n",
    "modules/neuro_refueling.py": "def run(**kwargs):\n    print('🧠 Neuro refueled by refactor_z.py placeholder.')\n    return {'status':'success', 'message':'Neuro refueled (placeholder)'}\n"
    # Add other modules here if needed by default
}


def ensure_dirs():
    # Ensure BASE itself exists first relative to script execution dir
    if not os.path.exists(BASE):
      os.makedirs(BASE) # Create BASE if it doesn't exist
      logger.info(f"[+] Base project directory created: {BASE}")
    else:
      logger.info(f"[i] Base project directory already exists: {BASE}")


    for d in DIR_STRUCTURE:
        path = os.path.join(BASE, d)
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            logger.info(f"[+] Directory created: {path}")
        else:
            logger.info(f"[i] Directory already exists: {path}")


def write_file(path, content, overwrite=False): # Added overwrite flag
    parent_dir = os.path.dirname(path)
    if parent_dir and not os.path.exists(parent_dir): # Check if parent_dir is not empty (e.g. for files in BASE)
        os.makedirs(parent_dir, exist_ok=True)

    if not os.path.exists(path) or overwrite:
        with open(path, "w", encoding="utf-8") as f:
            if isinstance(content, str):
                f.write(content)
            else: # Assume JSON serializable for lists/dicts
                json.dump(content, f, indent=2)
        logger.info(f"[✓] File {'written' if not os.path.exists(path) or overwrite else 'created'}: {path}")
    else:
        logger.info(f"[i] File already exists (skipped write): {path}")


def ensure_files(overwrite_existing_placeholders=False): # Flag to control overwriting
    for rel_path, content in FILES.items():
        abs_path = os.path.join(BASE, rel_path)
        write_file(abs_path, content, overwrite=overwrite_existing_placeholders) # Use overwrite flag


    for rel_path, content in MODULE_TEMPLATES.items():
        abs_path = os.path.join(BASE, rel_path)
        write_file(abs_path, content, overwrite=overwrite_existing_placeholders) # Use overwrite flag


def refactor_structure(overwrite_placeholders=False):
    logger.info("🔁 Initiating Refactor Z: Structure Rebuild (using refactor_z.py)")
    ensure_dirs()
    ensure_files(overwrite_existing_placeholders=overwrite_placeholders)
    logger.info("✅ Refactor Z (structure part) complete — боевое дерево создано.\n")


if __name__ == "__main__":
    setup_logging()
    # Set overwrite_placeholders to True if you want to reset default files to their template content.
    # Set to False to only create them if they are missing.
    # For the subtask, the previous state might have actual data, so False is safer unless specified.
    # The prompt implies a reset/creation, so True might be intended if files were changed.
    # Let's assume for this run, we want to ensure they exist but not overwrite if they do.
    # The original script used `if not os.path.exists(abs_path): write_file(...)`
    # which means overwrite_placeholders should be False to match that original intent.
    refactor_structure(overwrite_placeholders=False)
