import argparse
import sys
import os

# Add project root to sys.path to allow importing 'katana'
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from katana.cli import self_heal
from katana.cli import trader  # Added import for trader module
from katana.cli import misc  # Added import for misc module


def main():
    parser = argparse.ArgumentParser(description="Katana CLI tool.")
    subparsers = parser.add_subparsers(title="Modules", dest="module", required=True)

    # Self-heal module
    self_heal_parser = subparsers.add_parser(
        "self-heal", help="Self-healing daemon management."
    )
    self_heal_subparsers = self_heal_parser.add_subparsers(
        title="Commands", dest="command", required=True
    )

    # self-heal run
    run_parser = self_heal_subparsers.add_parser(
        "run", help="Run the self-healing daemon."
    )
    run_parser.add_argument(
        "--no-simulated-crash",
        action="store_true",
        help="Disable the simulated crash in the daemon main loop for smoother testing.",
    )
    run_parser.add_argument(
        "--daemon-sleep-interval",
        type=int,
        default=10,  # Default sleep interval in seconds
        help="Set the sleep interval for the daemon's main loop in seconds.",
    )
    run_parser.set_defaults(func=self_heal.run_daemon)

    # self-heal status
    status_parser = self_heal_subparsers.add_parser(
        "status", help="Get the status of the self-healing daemon."
    )
    status_parser.set_defaults(func=self_heal.get_status)

    # self-heal simulate-failure
    simulate_failure_parser = self_heal_subparsers.add_parser(
        "simulate-failure", help="Simulate a failure for the self-healing daemon."
    )
    simulate_failure_parser.set_defaults(func=self_heal.simulate_failure_command)

    # self-heal verify <task_id>
    # verify_parser = self_heal_subparsers.add_parser("verify", help="Manually verify a specific task.")
    # verify_parser.add_argument("task_id", type=str, help="The ID or name of the task to verify.")
    # verify_parser.add_argument(
    #     "--output-file",
    #     type=str,
    #     default=None, # Default is to print to stdout only and not save
    #     help="Optional path to save the katana_result.json output. If not provided, only prints to console."
    # )
    # verify_parser.set_defaults(func=self_heal.verify_task_command) # Temporarily commented out due to AttributeError

    # Trader module
    trader_parser = subparsers.add_parser("trader", help="Katana Trader management.")
    trader_subparsers = trader_parser.add_subparsers(
        title="Commands", dest="trader_command", required=True
    )

    # trader start
    trader_start_parser = trader_subparsers.add_parser(
        "start", help="Start the Katana Trader."
    )
    trader_start_parser.set_defaults(func=trader.start_trader)

    # trader status
    trader_status_parser = trader_subparsers.add_parser(
        "status", help="Get the status of the Katana Trader."
    )
    trader_status_parser.set_defaults(func=trader.get_trader_status)

    # trader stop
    trader_stop_parser = trader_subparsers.add_parser(
        "stop", help="Stop the Katana Trader."
    )
    trader_stop_parser.set_defaults(func=trader.stop_trader)

    # trader reset
    trader_reset_parser = trader_subparsers.add_parser(
        "reset", help="Reset the Katana Trader to a default state."
    )
    trader_reset_parser.set_defaults(func=trader.reset_trader)

    # trader dashboard
    trader_dashboard_parser = trader_subparsers.add_parser(
        "dashboard", help="Display trader dashboard."
    )
    trader_dashboard_parser.set_defaults(func=trader.display_dashboard)

    # Misc module - say command
    say_parser = subparsers.add_parser("say", help="Misc commands like say.")
    say_parser.add_argument("--text", type=str, required=True, help="Text to say.")
    say_parser.set_defaults(func=misc.say)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
