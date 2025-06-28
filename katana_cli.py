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
    run_parser.set_defaults(func=self_heal.run_daemon)

    # self-heal status
    status_parser = self_heal_subparsers.add_parser("status", help="Get the status of the self-healing daemon.")
    status_parser.set_defaults(func=self_heal.get_status)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
