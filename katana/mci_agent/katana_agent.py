# katana_agent.py
import json
import time
import os
import importlib.util
from pathlib import Path
from datetime import datetime
import uuid
import traceback
import shutil

from katana.utils.telemetry_provider import (
    setup_telemetry,
    get_logger,
    get_tracer,
    log_event,
    log_unstructured_message,
)
from opentelemetry._logs import SeverityNumber

# Path Constants
BASE_DIR = Path(__file__).resolve().parent
COMMANDS_DIR = BASE_DIR / "commands"
LOGS_DIR = BASE_DIR / "logs"
STATUS_DIR = BASE_DIR / "status"
MODULES_DIR = BASE_DIR / "modules"
PROCESSED_COMMANDS_DIR = BASE_DIR / "processed"
STATUS_FILE = STATUS_DIR / "agent_status.json"

# Global logger, initialized in main()
logger = None

# --- Default Structures for File Recovery ---
DEFAULT_STATUS = {
    "status": "idle_restored_from_internal_default",
    "timestamp": None,
    "notes": "This status file was generated from an internal default structure.",
}

# --- Phase 2: Combat Cycle Functions ---

def ensure_command_id(command):
    if not isinstance(command, dict):
        return
    if "id" not in command or not command["id"]:
        command["id"] = str(uuid.uuid4())

def execute_module(command):
    module_name = command.get("module")
    command_id = command.get("id")
    kwargs_from_command = command.get("args", {})

    if not isinstance(kwargs_from_command, dict):
        log_unstructured_message(
            logger,
            f"Args for module {module_name} is not a dictionary. Using empty kwargs.",
            SeverityNumber.WARN,
        )
        kwargs_from_command = {}

    kwargs_from_command["command_id"] = command_id
    kwargs_from_command["command_type"] = command.get("type")

    log_event(
        logger,
        "agent.module.execute.begin",
        body={
            "module_name": module_name,
            "command_id": command_id,
            "args": kwargs_from_command,
        },
        severity=SeverityNumber.DEBUG,
    )

    module_file_path = MODULES_DIR / f"{module_name}.py"

    try:
        if not module_file_path.exists():
            err_msg = f"Module file not found: {module_file_path}"
            log_event(logger, "agent.module.execute.error", {"command_id": command_id, "error": err_msg, "reason": "file_not_found"}, SeverityNumber.ERROR)
            return {"status": "error", "message": err_msg}

        spec = importlib.util.spec_from_file_location(module_file_path.stem, module_file_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        if hasattr(mod, "run") and callable(mod.run):
            module_result = mod.run(**kwargs_from_command)
            log_event(
                logger,
                "agent.module.execute.end",
                body={"module_name": module_name, "command_id": command_id, "raw_result": str(module_result)},
                severity=SeverityNumber.INFO,
            )

            success = isinstance(module_result, dict) and module_result.get("status") != "error" and module_result is not False
            return {"status": "success" if success else "error", "result": module_result}
        else:
            err_msg = f"Module '{module_name}' does not have a callable 'run' function."
            log_event(logger, "agent.module.execute.error", {"command_id": command_id, "error": err_msg, "reason": "no_run_function"}, SeverityNumber.ERROR)
            return {"status": "error", "message": err_msg}

    except Exception as e:
        error_details = traceback.format_exc()
        err_msg = f"{type(e).__name__}: {e}"
        log_event(
            logger,
            "agent.module.execute.exception",
            body={"command_id": command_id, "error": err_msg, "traceback": error_details},
            severity=SeverityNumber.ERROR,
        )
        return {"status": "error", "message": err_msg, "traceback": error_details}

def load_commands():
    log_unstructured_message(logger, "Entering load_commands function.", SeverityNumber.DEBUG)
    all_commands = []
    if not COMMANDS_DIR.exists():
        return all_commands

    for fpath in COMMANDS_DIR.rglob("*.json"):
        try:
            with fpath.open("r", encoding="utf-8") as f:
                command_data = json.load(f)
            if isinstance(command_data, dict):
                all_commands.append((fpath, command_data))
            else:
                log_event(logger, "agent.command.load.warning", {"file_path": str(fpath), "reason": "content_not_a_dict"}, SeverityNumber.WARN)
        except (json.JSONDecodeError, Exception) as e:
            log_event(logger, "agent.command.load.error", {"file_path": str(fpath), "error": str(e)}, SeverityNumber.WARN)

    if all_commands:
        log_unstructured_message(logger, f"Loaded {len(all_commands)} command(s).", SeverityNumber.INFO)
    return all_commands

def move_to_processed(original_path, data):
    try:
        relative_path = original_path.relative_to(COMMANDS_DIR)
        timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        archive_name = f"{original_path.stem}_{timestamp_str}{original_path.suffix}"
        dest_dir = PROCESSED_COMMANDS_DIR / relative_path.parent
        dest_dir.mkdir(parents=True, exist_ok=True)
        archive_path = dest_dir / archive_name

        with archive_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        original_path.unlink()
        log_event(logger, "agent.command.archive.success", {"command_id": data.get("id"), "original_path": str(original_path), "archive_path": str(archive_path)}, SeverityNumber.INFO)
        return True
    except Exception as e:
        log_event(
            logger,
            "agent.command.archive.error",
            body={"command_id": data.get("id"), "error": str(e), "traceback": traceback.format_exc()},
            severity=SeverityNumber.ERROR,
        )
        return False

def main(loop=False, delay=5):
    global logger
    logger_provider = setup_telemetry(service_name="katana-mci-agent")
    logger = get_logger("KatanaMCIAgent")
    tracer = get_tracer(__name__)

    try:
        with tracer.start_as_current_span("mci-agent.main") as main_span:
            main_span.set_attribute("agent.loop_mode", loop)
            main_span.set_attribute("agent.delay", delay)

            for d in [COMMANDS_DIR, STATUS_DIR, MODULES_DIR, PROCESSED_COMMANDS_DIR]:
                d.mkdir(exist_ok=True)

            log_unstructured_message(logger, "Katana agent started (MCI Enabled).", SeverityNumber.INFO)

            while True:
                log_unstructured_message(logger, "Start of main agent processing cycle.", SeverityNumber.DEBUG)
                try:
                    commands_to_process = load_commands()
                    if not commands_to_process:
                        log_unstructured_message(logger, "No command files found in this cycle.", SeverityNumber.DEBUG)
                    else:
                        log_unstructured_message(logger, f"Found {len(commands_to_process)} command file(s) to process.", SeverityNumber.INFO)

                    for command_path, command in commands_to_process:
                        ensure_command_id(command)
                        cmd_id = command.get("id")
                        cmd_type = command.get("type", "N/A")

                        log_event(logger, "agent.command.process.begin", {"command_id": cmd_id, "command_type": cmd_type, "file_path": str(command_path)})

                        success = False
                        summary = ""

                        if cmd_type == "trigger_module":
                            response = execute_module(command)
                            success = response.get("status") == "success"
                            summary = str(response.get("result") or response.get("message"))
                        else:
                            success = False
                            summary = f"Unknown command type: {cmd_type}"
                            log_event(logger, "agent.command.process.unknown", {"command_id": cmd_id, "command_type": cmd_type}, SeverityNumber.WARN)

                        command["executed_at"] = datetime.utcnow().isoformat()
                        command["status"] = "done" if success else "failed"
                        command["execution_summary"] = summary

                        log_event(
                            logger,
                            "agent.command.process.end",
                            {"command_id": cmd_id, "status": command["status"], "summary": summary},
                            severity=SeverityNumber.INFO if success else SeverityNumber.ERROR
                        )
                        move_to_processed(command_path, command)

                except Exception as e:
                    log_event(logger, "agent.loop.critical_error", {"error": str(e), "traceback": traceback.format_exc()}, SeverityNumber.FATAL)

                if not loop:
                    log_unstructured_message(logger, "Agent single run complete.", SeverityNumber.INFO)
                    break

                log_unstructured_message(logger, f"End of cycle. Sleeping for {delay} seconds.", SeverityNumber.DEBUG)
                time.sleep(delay)

            log_unstructured_message(logger, "Katana agent stopped.", SeverityNumber.INFO)
    finally:
        if logger_provider:
            logger_provider.shutdown()
            print("Telemetry provider shut down.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Katana Agent - MCI")
    parser.add_argument("--loop", action="store_true", help="Run agent in a continuous loop.")
    parser.add_argument("--delay", type=int, default=5, help="Delay in seconds for loop mode.")
    args = parser.parse_args()
    main(loop=args.loop, delay=args.delay)
