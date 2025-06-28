import argparse
import sys
import os

# Add project root to sys.path to allow importing 'katana'
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from katana.cli import self_heal

def main():
    parser = argparse.ArgumentParser(description="Katana CLI tool.")
    subparsers = parser.add_subparsers(title="Modules", dest="module", required=True)

    # Self-heal module
    self_heal_parser = subparsers.add_parser("self-heal", help="Self-healing daemon management.")
    self_heal_subparsers = self_heal_parser.add_subparsers(title="Commands", dest="command", required=True)

    # self-heal run
    run_parser = self_heal_subparsers.add_parser("run", help="Run the self-healing daemon.")
    run_parser.add_argument(
        "--no-simulated-crash",
        action="store_true",
        help="Disable the simulated crash in the daemon main loop for smoother testing."
    )
    run_parser.add_argument(
        "--daemon-sleep-interval",
        type=int,
        default=10, # Default sleep interval in seconds
        help="Set the sleep interval for the daemon's main loop in seconds."
    )
    run_parser.set_defaults(func=self_heal.run_daemon)

    # self-heal status
    status_parser = self_heal_subparsers.add_parser("status", help="Get the status of the self-healing daemon.")
    status_parser.set_defaults(func=self_heal.get_status)

    # self-heal verify <task_id>
    verify_parser = self_heal_subparsers.add_parser("verify", help="Manually verify a specific task.")
    verify_parser.add_argument("task_id", type=str, help="The ID or name of the task to verify.")
    verify_parser.add_argument(
        "--output-file",
        type=str,
        default=None, # Default is to print to stdout only and not save
        help="Optional path to save the katana_result.json output. If not provided, only prints to console."
    )
    verify_parser.set_defaults(func=self_heal.verify_task_command)


    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
