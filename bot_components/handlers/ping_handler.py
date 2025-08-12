from katana.core.contracts.commands import PingCommand
from katana.core.logging import StructuredLogger

def handle_ping(command: PingCommand, chat_id: int, logger: StructuredLogger):
    """
    Handles 'ping' commands.
    Теперь принимает провалидированный Pydantic-объект.
    """
    logger.info(
        f"handle_ping called",
        chat_id=chat_id,
        command_id=command.id,
        command_type=command.type
    )
    return "✅ 'ping' received."
