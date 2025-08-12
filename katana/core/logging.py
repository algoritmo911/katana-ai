import json
import sys
from .contracts.logs import LogEvent

# ==============================================================================
# Этап 3: "ГОЛОВА II: СТРАЖ ЛОГОВ" - КОНТРАКТЫ ДЛЯ ЛОГОВ (Реализация)
# ==============================================================================

class StructuredLogger:
    """
    Кастомный логгер, который использует Pydantic-контракт LogEvent
    для валидации и структурирования логов перед их выводом.
    """
    def _log(self, level: str, message: str, **kwargs):
        """
        Основной метод для создания и вывода лога.
        """
        try:
            # 1. Валидация по контракту "Стража Логов"
            log_entry = LogEvent(level=level, message=message, **kwargs)

            # 2. Сериализация в JSON
            # Pydantic's model_dump_json() удобно обрабатывает типы вроде datetime
            log_json = log_entry.model_dump_json(indent=None)

            # 3. Вывод в stdout/stderr
            # (в реальной системе здесь была бы отправка в ELK, Datadog и т.д.)
            output_stream = sys.stderr if level in ['ERROR', 'CRITICAL'] else sys.stdout
            print(log_json, file=output_stream)

        except Exception as e:
            # В случае, если даже логгер падает, выводим сырую ошибку.
            # Это критическая ситуация, т.к. система теряет наблюдаемость.
            print(f"!!! LOGGER FAILED !!! Reason: {e}", file=sys.stderr)
            print(f"Original log data: level={level}, message='{message}', kwargs={kwargs}", file=sys.stderr)

    def info(self, message: str, **kwargs):
        self._log('INFO', message, **kwargs)

    def warning(self, message: str, **kwargs):
        self._log('WARNING', message, **kwargs)

    def error(self, message: str, **kwargs):
        self._log('ERROR', message, **kwargs)

    def debug(self, message: str, **kwargs):
        self._log('DEBUG', message, **kwargs)

# Создаем синглтон-инстанс логгера для использования во всем приложении
logger = StructuredLogger()
