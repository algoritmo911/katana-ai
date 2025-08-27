from pydantic import BaseModel, Field

class Command(BaseModel):
    """
    Base class for all commands in the system.

    A command is an immutable data structure that represents a user's intent
    to perform a specific action. It contains all the necessary information
    for its corresponding handler to execute the action.
    """
    pass

class StartCommand(Command):
    """
    Command triggered when a user starts interacting with the bot.
    """
    user_id: int = Field(..., description="The unique ID of the user initiating the command.")
    user_name: str = Field(..., description="The username of the user.")
    chat_id: int = Field(..., description="The ID of the chat where the command was issued.")


class PingCommand(Command):
    """
    Command to check if the system is alive and responsive.
    """
    user_id: int = Field(..., description="The unique ID of the user sending the ping.")
    chat_id: int = Field(..., description="The ID of the chat where the command was issued.")
