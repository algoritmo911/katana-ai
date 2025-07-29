import argparse
from katana_cli.core.loader import load_commands

def main():
    parser = argparse.ArgumentParser(description="Katana AI CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    commands = load_commands()
    for name, cmd_class in commands.items():
        cmd_parser = subparsers.add_parser(name, help=cmd_class.help)
        cmd_instance = cmd_class(cmd_parser)
        cmd_parser.set_defaults(func=cmd_instance.run)

    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
