from katana.decorators.trace_command import trace_command

@trace_command
def say(args):
    """
    Prints the provided text to the terminal.
    """
    print(args.text)
