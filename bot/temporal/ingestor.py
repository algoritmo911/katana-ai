from datetime import datetime
from typing import Dict, Any
from .models import EventObject

class TimeIngestor:
    """
    Принимает и нормализует события из различных источников,
    присваивая им уникальный временной отпечаток (Chronos ID).
    """
    def __init__(self):
        print("TimeIngestor инициализирован.")

    def normalize_event(self, source: str, event_id: str, payload: Dict[str, Any], timestamp_utc: datetime = None) -> EventObject:
        """
        Основной метод для нормализации любого входящего события.
        Использует фабричный метод EventObject для создания экземпляра.
        """
        print(f"Нормализация события ID:{event_id} из источника:{source}...")

        event = EventObject.create(
            event_id=event_id,
            source=source,
            payload=payload,
            timestamp_utc=timestamp_utc
        )

        print(f"Событию присвоен Chronos ID: {event.chronos_id}")
        return event

    def process_realtime_stream(self, event_data: dict):
        """Обрабатывает одно событие из потока реального времени."""
        # Примерная структура входящих данных
        # { "event_id": "uuid", "payload": {...}, "temporal_source": "iso_timestamp", "origin_vector": "..." }

        # Этот метод будет вызываться, например, WebSocket-слушателем
        return self.normalize_event(
            source='realtime_stream',
            event_id=event_data.get('event_id', 'unknown_id'),
            payload=event_data.get('payload', {}),
            timestamp_utc=datetime.fromisoformat(event_data.get('temporal_source')) if event_data.get('temporal_source') else None
        )

    def process_historical_batch(self, batch_data: list):
        """Обрабатывает пакет исторических данных."""
        normalized_events = []
        for event_data in batch_data:
            # Предполагаем, что структура event_data такая же, как в realtime
            normalized_events.append(self.process_realtime_stream(event_data))
        return normalized_events

# Пример использования
if __name__ == '__main__':
    ingestor = TimeIngestor()

    # 1. Симуляция события из реального времени
    print("\n--- Тест события реального времени ---")
    realtime_event_data = {
        "event_id": "commit-abc123",
        "payload": {"author": "Jules", "message": "feat: Implemented TimeIngestor"},
        "temporal_source": "2025-08-20T14:30:00Z",
        "origin_vector": "logical_node_id:dev-machine-1"
    }
    normalized_event = ingestor.process_realtime_stream(realtime_event_data)
    print("Нормализованное событие:")
    print(normalized_event.model_dump_json(indent=2))

    # 2. Симуляция пакетной загрузки
    print("\n--- Тест пакетной загрузки ---")
    historical_batch = [
        {
            "event_id": "chat-msg-001",
            "payload": {"user": "Alex", "text": "We need to discuss Project Chimera."},
            "temporal_source": "2025-08-10T14:35:00Z"
        },
        {
            "event_id": "jira-ticket-456",
            "payload": {"assignee": "Jules", "status": "In Progress", "title": "Fix temporal anomalies"},
            "temporal_source": "2025-08-11T10:00:00Z"
        }
    ]
    normalized_batch = ingestor.process_historical_batch(historical_batch)
    print("Нормализованный пакет:")
    for event in normalized_batch:
        print(event.model_dump_json(indent=2))
