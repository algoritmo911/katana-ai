import argparse
from katana_cli.commands import status, cancel, flush, log

def main():
    parser = argparse.ArgumentParser(description="Katana AI CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Status command
    status_parser = subparsers.add_parser("status", help="Show system status")
    status_parser.set_defaults(func=status.run)

    # Cancel command
    cancel_parser = subparsers.add_parser("cancel", help="Cancel the current active task")
    cancel_parser.set_defaults(func=cancel.run)

    # Flush command
    flush_parser = subparsers.add_parser("flush", help="Flush temporary data/logs")
    flush_parser.set_defaults(func=flush.run)

    # Log command
    log_parser = subparsers.add_parser("log", help="Show last 10 logs")
    log_parser.set_defaults(func=log.run)

    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
