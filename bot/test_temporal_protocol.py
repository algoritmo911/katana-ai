import pytest
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from bot.temporal.models import EventObject
from bot.temporal.fabric import TimeFabric

# Устанавливаем переменные окружения до импорта модулей бота
from dotenv import load_dotenv
load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = "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"


@pytest.mark.integration
def test_time_fabric_infers_and_validates_causality(monkeypatch):
    """
    Тестирует, что TimeFabric использует CausalConsistencyEngine
    для установки логичной причинно-следственной связи.
    """
    # Используем monkeypatch для надежной установки переменных перед вызовом
    monkeypatch.setenv("OPENAI_API_KEY", "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")

    # 1. Создаем два очевидно связанных события
    event_a = EventObject.create(
        source="jira_ticket",
        event_id="PROJ-123",
        payload={"type": "bug", "summary": "Generator fails on missing template"},
        timestamp_utc=datetime.now(timezone.utc)
    )

    event_b = EventObject.create(
        source="github_commit",
        event_id="commit-d4e5f6",
        payload={"author": "Jules", "message": "fix: Added error handling for missing templates", "reference": "PROJ-123"},
        timestamp_utc=datetime.now(timezone.utc) + timedelta(hours=1)
    )

    # 2. Инициализируем Ткань Времени
    fabric = TimeFabric()

    # 3. Добавляем события
    # Мокаем _infer_causality, чтобы не делать реальные вызовы LLM,
    # а затем проверим, что CausalConsistencyEngine был вызван с правильными данными.
    # Это более сложный тест, для начала проверим сквозной вызов.

    # Для этого теста мы делаем реальные вызовы к LLM
    fabric.add_event(event_a)
    fabric.add_event(event_b)

    # 4. Проверяем результат
    # Главная проверка: была ли создана связь от тикета к коммиту?
    # Мы ожидаем, что LLM увидит ссылку "PROJ-123" в коммите и поймет связь,
    # а CausalConsistencyEngine подтвердит, что она логична.
    assert fabric.graph.has_edge(event_a.chronos_id, event_b.chronos_id), \
        "Причинно-следственная связь между JIRA-тикетом и коммитом не была установлена."

    edge_data = fabric.graph.get_edge_data(event_a.chronos_id, event_b.chronos_id)
    assert "justification" in edge_data
    assert isinstance(edge_data['confidence'], float)
    assert edge_data['confidence'] > 0.5 # Ожидаем высокую уверенность

    print(f"\nСвязь успешно установлена с обоснованием: '{edge_data['justification']}' и уверенностью: {edge_data['confidence']:.2f}")
