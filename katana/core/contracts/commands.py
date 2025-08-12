from pydantic import BaseModel, Field
from typing import Union, Literal

# ==============================================================================
# Этап 1: "ГОЛОВА I: СТРАЖ ВХОДА" - ФОРМАЛЬНЫЕ КОНТРАКТЫ КОМАНД
# ==============================================================================

# ------------------------------------------------------------------------------
# Модели для аргументов (`args`) каждой команды
# ------------------------------------------------------------------------------

class PingArgs(BaseModel):
    """Аргументы для команды ping. В данном случае, пустые."""
    pass

class LogEventArgs(BaseModel):
    """Аргументы для команды log_event."""
    level: str = Field(..., description="Уровень лога (e.g., 'info', 'warning', 'error').")
    message: str = Field(..., description="Сообщение лога.")

class MindClearingArgs(BaseModel):
    """Аргументы для команды mind_clearing."""
    duration: str = Field(..., description="Длительность сессии (e.g., '5m', '10m').")

# ------------------------------------------------------------------------------
# Общая модель команды и специфичные модели для каждой команды
# ------------------------------------------------------------------------------

class BaseCommand(BaseModel):
    """
    Базовый контракт для всех команд.
    Описывает общую структуру, которую "Гермес" ожидает от любого входящего запроса.
    """
    id: Union[str, int] = Field(..., description="Уникальный идентификатор команды.")
    module: str = Field(..., description="Модуль, к которому относится команда.")
    # `args` пока оставим как BaseModel, чтобы специфичные команды могли его переопределить.
    args: BaseModel

class PingCommand(BaseCommand):
    """Контракт для команды 'ping'."""
    type: Literal['ping'] = 'ping'
    args: PingArgs = PingArgs()

class LogEventCommand(BaseCommand):
    """Контракт для команды 'log_event'."""
    type: Literal['log_event'] = 'log_event'
    args: LogEventArgs

class MindClearingCommand(BaseCommand):
    """Контракт для команды 'mind_clearing'."""
    type: Literal['mind_clearing'] = 'mind_clearing'
    args: MindClearingArgs

# ------------------------------------------------------------------------------
# Фабрика для выбора нужного контракта на основе поля 'type'
# ------------------------------------------------------------------------------

COMMAND_MODELS = {
    'ping': PingCommand,
    'log_event': LogEventCommand,
    'mind_clearing': MindClearingCommand,
}

def get_command_model(command_data: dict):
    """
    Возвращает соответствующую Pydantic модель команды на основе поля 'type'.
    """
    command_type = command_data.get('type')
    return COMMAND_MODELS.get(command_type)
