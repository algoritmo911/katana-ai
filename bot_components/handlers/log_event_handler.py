from katana.core.contracts.commands import LogEventCommand
from katana.core.logging import StructuredLogger

def handle_log_event(command: LogEventCommand, chat_id: int, logger: StructuredLogger):
    """
    Handles 'log_event' commands.
    Принимает провалидированный Pydantic-объект.
    """
    # Теперь мы можем безопасно обращаться к command.args.level и command.args.message,
    # так как "Страж Входа" уже гарантировал их наличие и тип.
    logger.info(
        f"handle_log_event called: {command.args.message}",
        chat_id=chat_id,
        command_id=command.id,
        command_type=command.type,
        extra={
            "log_level": command.args.level,
            "log_message": command.args.message
        }
    )
    # В реальной системе здесь была бы логика записи этого события в другую систему.
    # Сейчас просто логируем факт его получения.
