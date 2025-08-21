import os
from datetime import datetime, timedelta
from bot.temporal.ingestor import TimeIngestor
from bot.temporal.fabric import TimeFabric

from dotenv import load_dotenv

def main():
    """
    Демонстрирует полный цикл работы "Ткачей Времени":
    Прием событий -> Нормализация -> Построение графа -> Анализ.
    """
    # ПРИМЕЧАНИЕ ДЛЯ АРХИТЕКТОРА: В этом демонстрационном скрипте ключи API
    # загружаются через load_dotenv(). В реальном продакшн-окружении
    # эти переменные должны быть предоставлены через безопасную среду,
    # например, Doppler, как мы и обсуждали.
    load_dotenv()

    print("--- Запуск демонстрации 'Ткачи Времени' ---")

    ingestor = TimeIngestor()
    fabric = TimeFabric()

    # 1. Симуляция поступления разнородных событий во времени
    print("\n[Шаг 1: Симуляция потока событий]")

    events_data = [
        {
            "source": "architect_directive",
            "event_id": "DIR-001",
            "payload": {"title": "Миссия 'Кронос'", "goal": "Создать генератор n8n-воркфлоу"},
            "timestamp_utc": datetime.utcnow()
        },
        {
            "source": "github_commit",
            "event_id": "commit-a1b2c3",
            "payload": {"author": "Jules", "message": "feat: Implemented N8nBlueprintGenerator class"},
            "timestamp_utc": datetime.utcnow() + timedelta(hours=2)
        },
        {
            "source": "jira_ticket",
            "event_id": "PROJ-123",
            "payload": {"type": "bug", "summary": "Generator fails on missing template", "status": "OPEN"},
            "timestamp_utc": datetime.utcnow() + timedelta(hours=4)
        },
        {
            "source": "github_commit",
            "event_id": "commit-d4e5f6",
            "payload": {"author": "Jules", "message": "fix: Added error handling for missing templates", "reference": "PROJ-123"},
            "timestamp_utc": datetime.utcnow() + timedelta(hours=6)
        },
        {
            "source": "qa_report",
            "event_id": "QA-005",
            "payload": {"test_case": "test_missing_template", "result": "PASS", "notes": "Fix confirmed"},
            "timestamp_utc": datetime.utcnow() + timedelta(hours=8)
        }
    ]

    # 2. Обработка и добавление событий в ткань времени
    print("\n[Шаг 2: Построение Ткани Времени]")
    all_normalized_events = []
    for data in events_data:
        normalized_event = ingestor.normalize_event(**data)
        all_normalized_events.append(normalized_event)
        fabric.add_event(normalized_event)

    # 3. Анализ графа
    print("\n[Шаг 3: Анализ графа]")
    gravity_scores = fabric.calculate_gravity_scores()

    # Сортируем события по влиятельности
    sorted_events = sorted(
        gravity_scores.items(),
        key=lambda item: item[1],
        reverse=True
    )

    print("\n--- Топ-5 самых влиятельных событий ('точки гравитации') ---")
    for node_id, score in sorted_events[:5]:
        node_data = fabric.graph.nodes[node_id]
        print(f"  - [{node_data['source']}:{node_data['event_id']}] - Gravity: {score:.4f}")

    # 4. Получение контекста для конкретного события
    print("\n--- 'Окно внимания' для события фикса бага ---")
    # Ищем нужный chronos_id по исходному event_id
    bug_fix_event_chronos_id = None
    for event in all_normalized_events:
        if event.event_id == 'commit-d4e5f6':
            bug_fix_event_chronos_id = event.chronos_id
            break

    if bug_fix_event_chronos_id:
        attention_window = fabric.get_attention_window(bug_fix_event_chronos_id, k=3)
        print(f"Событие: Фикс бага (commit-d4e5f6)")
    else:
        attention_window = []
        print("Событие фикса бага не найдено.")
    print("Наиболее связанные события:")
    for node_id in attention_window:
        node_data = fabric.graph.nodes[node_id]
        print(f"  - [{node_data['source']}:{node_data['event_id']}] (Gravity: {node_data.get('gravity_score', 0):.4f})")

    # 5. Сохранение результата
    fabric.save_graph()

    print("\n--- Демонстрация завершена ---")

if __name__ == '__main__':
    main()
