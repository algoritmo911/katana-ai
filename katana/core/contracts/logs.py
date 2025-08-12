from pydantic import BaseModel, Field
from typing import Optional, Union, Dict, Any
from datetime import datetime

# ==============================================================================
# Этап 3: "ГОЛОВА II: СТРАЖ ЛОГОВ" - КОНТРАКТЫ ДЛЯ ЛОГОВ
# ==============================================================================

class LogEvent(BaseModel):
    """
    Контракт для структурированного лога.
    Гарантирует, что все логи в системе имеют единый, машиночитаемый формат.
    """
    timestamp: datetime = Field(..., default_factory=datetime.utcnow)
    level: str = Field(..., description="Уровень лога: 'INFO', 'WARNING', 'ERROR', 'DEBUG'.")
    message: str = Field(..., description="Основное сообщение лога.")

    # Контекстная информация
    command_id: Optional[Union[str, int]] = None
    chat_id: Optional[int] = None
    command_type: Optional[str] = None

    # Дополнительные данные для отладки
    extra: Dict[str, Any] = {}
