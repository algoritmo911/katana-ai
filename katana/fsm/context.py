from typing import Callable, Coroutine, Any, Awaitable


class FSMContext:
    """
    Provides FSM states with a controlled interface to the outside world (e.g., the bot).
    This decouples the state logic from the bot framework.
    """

    def __init__(
        self,
        chat_id: int,
        # A function to send a reply back to the user.
        reply_func: Callable[[str], Awaitable[None]],
        # A function to execute a shell command and get the result.
        exec_func: Callable[[str], Awaitable[str]],
    ):
        """
        Initializes the context.

        Args:
            chat_id: The ID of the current chat.
            reply_func: An async function to send a message to the user.
            exec_func: An async function to execute a shell command.
        """
        self.chat_id = chat_id
        self.reply = reply_func
        self.execute = exec_func
        # This context can be expanded with more functions as needed,
        # e.g., database access, etc.
