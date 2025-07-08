# Katana Fatigue Analyzer Module

Этот модуль предназначен для анализа истории взаимодействий пользователя с ботом Katana с целью выявления признаков когнитивной перегрузки или усталости пользователя.

## Основные компоненты

-   **`schemas.py`**: Определяет структуры данных (Pydantic модели) для сообщений, сессий и итоговых метрик усталости.
    -   `MessageInput`: Представление одного сообщения.
    -   `SessionData`: Данные одной сессии взаимодействия.
    -   `FatigueMetricsOutput`: Итоговые рассчитанные метрики для одной сессии.
-   **`metrics.py`**: Содержит функции для расчета различных метрик, таких как:
    -   Частота команд (`command_frequency`)
    -   Время реакции пользователя (`reaction_time`)
    -   Уровень ошибок (`error_rate`)
    -   Длительность сессии (`session_duration`)
    -   Частота смены контекста (`context_switch_frequency`)
    -   Соотношение сообщений пользователь/бот (`user_bot_ratio`)
    -   Общий балл усталости (`fatigue_score`)
-   **`collector.py`**: Ядро модуля.
    -   `FatigueCollector`: Класс, который:
        -   Извлекает историю сообщений из `MemoryManager`.
        -   Сегментирует историю на сессии на основе времени неактивности.
        -   Анализирует каждую сессию, вызывая функции из `metrics.py`.
        -   Формирует отчеты `FatigueMetricsOutput`.
        -   Логирует предупреждения при обнаружении признаков усталости.
    -   `FatigueStorage` (абстрактный класс) и `LocalFileStorage` (реализация): Интерфейс и класс для сохранения рассчитанных метрик (в данном случае, в локальный JSON-файл).
-   **`runner.py`**: CLI-интерфейс для запуска анализа.
    -   Позволяет указать `chat_id` пользователя для анализа.
    -   Поддерживает сохранение результатов в JSON-файл.
    -   Настраивается через аргументы командной строки (например, параметры подключения к Redis для `MemoryManager`).

## Как использовать (CLI)

Анализатор можно запустить из командной строки. Убедитесь, что вы находитесь в корневой директории проекта `katana-ai`.

```bash
python -m src.monitoring.fatigue_analyzer.runner --chat-id <ID_ЧАТА_ПОЛЬЗОВАТЕЛЯ> --save --output-file reports/fatigue_analysis_<ID_ЧАТА_ПОЛЬЗОВАТЕЛЯ>.json --log-level INFO
```

**Аргументы командной строки для `runner.py`:**

-   `--chat-id CHAT_ID` (обязательный): ID чата пользователя для анализа.
-   `--save`: Если указан, результаты анализа будут сохранены в JSON-файл.
-   `--output-file OUTPUT_FILE`: Путь к файлу для сохранения результатов (по умолчанию: `fatigue_analysis_report.json` в текущей директории). Рекомендуется использовать поддиректорию `reports/`.
-   `--log-level LEVEL`: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL; по умолчанию: INFO).
-   `--redis-host HOST`: Хост Redis (по умолчанию: `localhost` или из `REDIS_HOST`).
-   `--redis-port PORT`: Порт Redis (по умолчанию: `6379` или из `REDIS_PORT`).
-   `--redis-db DB`: Номер базы данных Redis (по умолчанию: `0` или из `REDIS_DB`).
-   `--redis-password PASSWORD`: Пароль Redis (по умолчанию: `None` или из `REDIS_PASSWORD`).

**Пример запуска с использованием MOCK данных (если реальный MemoryManager недоступен):**

Если `MemoryManager` не может подключиться к Redis или не настроен, `FatigueCollector` и `runner.py` попытаются использовать встроенную MOCK-реализацию `MemoryManager`, которая возвращает тестовые данные для `chat_id="test_chat_with_data"`.

```bash
python -m src.monitoring.fatigue_analyzer.runner --chat-id test_chat_with_data --save --output-file reports/fatigue_analysis_MOCK.json --log-level DEBUG
```

## Тестирование

Юнит-тесты для функций расчета метрик находятся в `tests/monitoring/test_fatigue_metrics.py`. Для запуска тестов (из корневой директории проекта):

```bash
python -m unittest tests.monitoring.test_fatigue_metrics
# или
# pytest tests/monitoring/test_fatigue_metrics.py (если используется pytest)
```

## Будущие улучшения

-   Интеграция с Supabase для хранения и агрегации метрик.
-   Более сложные алгоритмы для расчета `fatigue_score`.
-   Более продвинутый анализ "отклонения от цели".
-   Визуализация метрик (дэшборд).
-   Автоматический периодический запуск анализа (например, через cron или Celery).
```
