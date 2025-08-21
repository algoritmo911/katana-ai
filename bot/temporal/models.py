from pydantic import BaseModel, Field
from typing import Any, Dict
from datetime import datetime
import hashlib
import json

class EventObject(BaseModel):
    """
    Нормализованное представление любого события, поступающего в систему.
    """
    chronos_id: str = Field(..., description="Уникальный, детерминированный временной отпечаток события.")
    event_id: str = Field(..., description="Оригинальный ID события из исходной системы.")
    source: str = Field(..., description="Источник события (например, 'github', 'telegram', 'jira').")
    timestamp_utc: datetime = Field(..., description="Время события в UTC.")
    payload: Dict[str, Any] = Field(..., description="Содержимое события в формате словаря.")

    @classmethod
    def create(cls, event_id: str, source: str, payload: Dict[str, Any], timestamp_utc: datetime = None):
        """
        Фабричный метод для создания EventObject с вычислением ChronoHash.
        """
        if timestamp_utc is None:
            timestamp_utc = datetime.utcnow()

        # Реализация ChronoHash
        # Хэш создается из контента и временной метки для детерминизма
        payload_str = json.dumps(payload, sort_keys=True)
        timestamp_iso = timestamp_utc.isoformat()

        hasher = hashlib.sha256()
        hasher.update(source.encode('utf-8'))
        hasher.update(event_id.encode('utf-8'))
        hasher.update(payload_str.encode('utf-8'))
        hasher.update(timestamp_iso.encode('utf-8'))

        chronos_id = hasher.hexdigest()

        return cls(
            chronos_id=chronos_id,
            event_id=event_id,
            source=source,
            timestamp_utc=timestamp_utc,
            payload=payload
        )
