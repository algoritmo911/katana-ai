from katana.core.contracts.commands import MindClearingCommand
from katana.core.logging import StructuredLogger

def handle_mind_clearing(command: MindClearingCommand, chat_id: int, logger: StructuredLogger):
    """
    Handles 'mind_clearing' commands.
    Принимает провалидированный Pydantic-объект.
    """
    # "Страж Входа" гарантирует, что command.args.duration существует.
    logger.info(
        f"handle_mind_clearing called for duration {command.args.duration}",
        chat_id=chat_id,
        command_id=command.id,
        command_type=command.type,
        extra={"duration": command.args.duration}
    )
    return f"✅ 'mind_clearing' for {command.args.duration} processed."
