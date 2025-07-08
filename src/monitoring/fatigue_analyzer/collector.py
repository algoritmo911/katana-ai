import logging
import json # Для LocalFileStorage
import os # Для LocalFileStorage
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any

# Предполагается, что MemoryManager находится в src/memory/memory_manager.py
# и может быть импортирован. Нам нужен доступ к его методу get_history.
# --- Начало блока для импорта MemoryManager ---
try:
    from src.memory.memory_manager import MemoryManager
    # Проверка, что это не заглушка
    if MemoryManager.__module__ == __name__: # Если MemoryManager определен в этом же файле (заглушка)
        raise ImportError("Using local mock MemoryManager, attempting to find real one.")
except ImportError:
    try:
        # Это для случая, когда collector.py может быть запущен из разных мест,
        # и PYTHONPATH может быть настроен по-разному.
        # Попытка импорта из родительской директории src, если collector.py внутри src/monitoring/fatigue_analyzer
        from ....memory.memory_manager import MemoryManager as ParentMemoryManager # noqa
        MemoryManager = ParentMemoryManager
        if MemoryManager.__module__ == __name__:
             raise ImportError("Using local mock MemoryManager again.")
    except (ImportError, ValueError): # ValueError может быть из-за относительного импорта выше максимального уровня
        logging.warning(
            "Real MemoryManager not found by typical import paths. Using MOCK MemoryManager. "
            "Ensure 'src' is in PYTHONPATH or MemoryManager is installed correctly."
        )
        class MemoryManager: # type: ignore
            def __init__(self, *args, **kwargs):
                logging.info("Using MOCK MemoryManager.")

            def get_history(self, chat_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
                logging.warning(f"MOCK MemoryManager: get_history called for {chat_id}, returning sample data if chat_id is 'test_chat_with_data'.")
                if chat_id == "test_chat_with_data":
                    now = datetime.now(timezone.utc)
                    return [
                        {"role": "user", "content": "Hello", "timestamp": (now - timedelta(minutes=65)).isoformat()},
                        {"role": "assistant", "content": "Hi there!", "timestamp": (now - timedelta(minutes=64, seconds=30)).isoformat()},
                        {"role": "user", "content": "How are you?", "timestamp": (now - timedelta(minutes=62)).isoformat()},
                        # Пауза более 30 минут для создания новой сессии
                        {"role": "user", "content": "Long pause message, new session", "timestamp": (now - timedelta(minutes=10)).isoformat()},
                        {"role": "assistant", "content": "I am fine, thank you!", "timestamp": (now - timedelta(minutes=9)).isoformat()},
                        {"role": "user", "content": "Good to hear. /mind_clearing", "timestamp": (now - timedelta(minutes=8)).isoformat()},
                        {"role": "assistant", "content": "Context cleared. Error in processing.", "timestamp": (now - timedelta(minutes=7)).isoformat()},
                    ]
                return []

            def add_message_to_history(self, chat_id: str, message: Dict[str, Any]):
                logging.warning(f"MOCK MemoryManager: add_message_to_history called for {chat_id}.")
                pass

            def clear_history(self, chat_id: str):
                logging.warning(f"MOCK MemoryManager: clear_history called for {chat_id}.")
                pass
# --- Конец блока для импорта MemoryManager ---


from .schemas import MessageInput, SessionData, FatigueMetricsOutput
from . import metrics as fatigue_metrics

logger = logging.getLogger(__name__)


class FatigueCollector:
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager

    def _fetch_messages_from_memory(self, chat_id: str) -> List[MessageInput]:
        raw_history = self.memory_manager.get_history(chat_id)
        processed_messages: List[MessageInput] = []
        for msg_data in raw_history:
            try:
                ts_str = msg_data.get("timestamp")
                if not ts_str:
                    logger.warning(f"Message for chat {chat_id} missing timestamp: {msg_data}")
                    continue

                timestamp = datetime.fromisoformat(ts_str.replace("Z", "+00:00")) # Pydantic/Python 3.11+ handle Z, older may need +00:00

                if timestamp.tzinfo is None: # Should not happen if fromisoformat worked with Z or +00:00
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                else:
                    timestamp = timestamp.astimezone(timezone.utc)

                processed_messages.append(
                    MessageInput(
                        role=msg_data.get("role", "unknown"),
                        content=msg_data.get("content", ""),
                        timestamp=timestamp,
                    )
                )
            except Exception as e:
                logger.error(f"Failed to process message for chat {chat_id}: {msg_data}. Error: {e}", exc_info=True)

        processed_messages.sort(key=lambda m: m.timestamp)
        return processed_messages

    def _segment_sessions(
        self, messages: List[MessageInput], chat_id: str, inactivity_threshold_minutes: int = 30
    ) -> List[SessionData]:
        if not messages:
            return []

        sessions: List[SessionData] = []
        current_session_messages: List[MessageInput] = []

        for msg in messages:
            # Убедимся, что msg.timestamp имеет timezone info (UTC)
            msg_ts = msg.timestamp
            if msg_ts.tzinfo is None: msg_ts = msg_ts.replace(tzinfo=timezone.utc)

            if not current_session_messages: # Начало первой сессии или новой сессии
                current_session_messages.append(msg)
                continue

            prev_msg_ts = current_session_messages[-1].timestamp
            if prev_msg_ts.tzinfo is None: prev_msg_ts = prev_msg_ts.replace(tzinfo=timezone.utc)

            time_diff_minutes = (msg_ts - prev_msg_ts).total_seconds() / 60.0

            if time_diff_minutes > inactivity_threshold_minutes:
                session_start_time = current_session_messages[0].timestamp
                session_end_time = current_session_messages[-1].timestamp
                session_id = f"{chat_id}_{session_start_time.strftime('%Y%m%dT%H%M%S')}"
                sessions.append(
                    SessionData(
                        session_id=session_id, chat_id=chat_id,
                        start_time=session_start_time, end_time=session_end_time,
                        messages=list(current_session_messages),
                    )
                )
                current_session_messages = [msg] # Начинаем новую сессию с текущего сообщения
            else:
                current_session_messages.append(msg)

        if current_session_messages:
            session_start_time = current_session_messages[0].timestamp
            session_end_time = current_session_messages[-1].timestamp
            session_id = f"{chat_id}_{session_start_time.strftime('%Y%m%dT%H%M%S')}"
            sessions.append(
                SessionData(
                    session_id=session_id, chat_id=chat_id,
                    start_time=session_start_time, end_time=session_end_time,
                    messages=list(current_session_messages),
                )
            )
        return sessions

    def analyze_session(self, session_data: SessionData) -> FatigueMetricsOutput:
        messages = session_data.messages

        freq_5m = fatigue_metrics.calculate_command_frequency(messages, 5, session_data.end_time)
        freq_10m = fatigue_metrics.calculate_command_frequency(messages, 10, session_data.end_time)
        freq_1h = fatigue_metrics.calculate_command_frequency(messages, 60, session_data.end_time)
        avg_rt, med_rt, std_rt = fatigue_metrics.calculate_reaction_times(messages)
        err_rate = fatigue_metrics.calculate_error_rate(messages)
        duration_min = fatigue_metrics.calculate_session_duration(session_data.start_time, session_data.end_time)
        switches = fatigue_metrics.calculate_context_switch_frequency(messages)
        ratio, ratio_warn = fatigue_metrics.calculate_user_bot_ratio(messages)
        total_msgs = len(messages)
        user_msgs = len(fatigue_metrics.get_user_messages(messages))
        bot_msgs = len(fatigue_metrics.get_assistant_messages(messages))

        calculated_metrics_dict = {
            "average_reaction_time_sec": avg_rt, "error_rate": err_rate,
            "context_switches": switches, "user_bot_message_ratio": ratio,
            "command_frequency_10m": freq_10m, # Используем 10м для скора по умолчанию
        }
        fatigue_score_val = fatigue_metrics.calculate_fatigue_score(calculated_metrics_dict)

        return FatigueMetricsOutput(
            user_id=session_data.chat_id, session_id=session_data.session_id,
            timestamp=datetime.now(timezone.utc),
            command_frequency_5m=freq_5m, command_frequency_10m=freq_10m, command_frequency_1h=freq_1h,
            average_reaction_time_sec=avg_rt, median_reaction_time_sec=med_rt, std_reaction_time_sec=std_rt,
            error_rate=err_rate, session_duration_min=duration_min, context_switches=switches,
            user_bot_message_ratio=ratio, user_bot_ratio_warning=ratio_warn,
            fatigue_score=fatigue_score_val,
            total_messages_in_session=total_msgs, user_messages_in_session=user_msgs,
            bot_messages_in_session=bot_msgs
        )

    def process_user_fatigue(self, chat_id: str) -> List[FatigueMetricsOutput]:
        logger.info(f"Starting fatigue analysis for chat_id: {chat_id}")
        messages = self._fetch_messages_from_memory(chat_id)
        if not messages:
            logger.info(f"No messages found for chat_id: {chat_id}.")
            return []
        logger.info(f"Fetched {len(messages)} messages for chat_id: {chat_id}.")

        sessions = self._segment_sessions(messages, chat_id)
        if not sessions:
            logger.info(f"No sessions segmented for chat_id: {chat_id}.")
            return []
        logger.info(f"Segmented into {len(sessions)} sessions for chat_id: {chat_id}.")

        all_fatigue_reports: List[FatigueMetricsOutput] = []
        for session_data in sessions:
            logger.debug(f"Analyzing session_id: {session_data.session_id} ({len(session_data.messages)} messages)")
            report = self.analyze_session(session_data)
            all_fatigue_reports.append(report)

            # Логирование предупреждений о перегрузке
            log_fatigue_alert = False
            conditions_met = 0
            if report.error_rate is not None and report.error_rate > 0.25: conditions_met +=1 # Более 25% ошибок
            if report.average_reaction_time_sec is not None and report.average_reaction_time_sec < 5 : conditions_met +=0.5 # Очень быстро, возможно копипаст или не вдумывается
            if report.average_reaction_time_sec is not None and report.average_reaction_time_sec > 60 : conditions_met +=1 # Реакция > 60 сек
            if report.context_switches is not None and report.context_switches > 1 : conditions_met +=1 # Больше 1 сброса контекста

            if conditions_met >= 2: # Если хотя бы 2 условия изменены в сторону "усталости"
                log_fatigue_alert = True

            if report.fatigue_score is not None and report.fatigue_score > 0.65: # Или если общий скор высокий
                log_fatigue_alert = True

            if log_fatigue_alert:
                 logger.warning(
                    f"[FATIGUE ALERT] Potential fatigue for user {report.user_id}, session {report.session_id}. "
                    f"Score: {report.fatigue_score:.2f if report.fatigue_score else 'N/A'}. "
                    f"Details: Errors={report.error_rate:.2% if report.error_rate else 'N/A'}, "
                    f"AvgReactTime={report.average_reaction_time_sec:.1f}s if report.average_reaction_time_sec else 'N/A'}, "
                    f"Switches={report.context_switches if report.context_switches is not None else 'N/A'}, "
                    f"User/Bot Ratio Warn: {report.user_bot_ratio_warning}"
                )
        logger.info(f"Completed fatigue analysis for chat_id: {chat_id}. Generated {len(all_fatigue_reports)} reports.")
        return all_fatigue_reports

# --- Storage Interface and Implementation ---
class FatigueStorage:
    def save_batch(self, metrics_reports: List[FatigueMetricsOutput]) -> None:
        raise NotImplementedError

class LocalFileStorage(FatigueStorage):
    def __init__(self, filepath: str):
        self.filepath = filepath
        # Убедимся, что директория для файла существует
        output_dir = os.path.dirname(self.filepath)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"Created directory for output file: {output_dir}")

    def save_batch(self, metrics_reports: List[FatigueMetricsOutput]) -> None:
        # Перезаписываем файл всем набором отчетов для данного запуска анализа
        # (например, все сессии одного пользователя)
        # Если нужно дописывать, логика усложняется (чтение, добавление, запись).
        # Для MVP перезапись проще.

        # Преобразуем Pydantic модели в словари для JSON сериализации
        # Используем model_dump() для Pydantic v2 или .dict() для v1
        reports_to_save = []
        for report in metrics_reports:
            try:
                reports_to_save.append(report.model_dump(mode="json")) # Pydantic v2
            except AttributeError:
                reports_to_save.append(report.dict()) # Pydantic v1 (или json.loads(report.json()))


        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(reports_to_save, f, indent=2, ensure_ascii=False)
            logger.info(f"Successfully saved {len(metrics_reports)} fatigue reports to {self.filepath}")
        except IOError as e:
            logger.error(f"Failed to save fatigue reports to {self.filepath}: {e}", exc_info=True)
        except Exception as e: # Catch any other unexpected errors during saving
            logger.error(f"Unexpected error during saving fatigue reports to {self.filepath}: {e}", exc_info=True)


if __name__ == "__main__":
    # Настройка базового логирования для тестирования collector.py
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Используем MOCK MemoryManager, который определен выше
    mock_mm = MemoryManager() # type: ignore

    # Добавим тестовые данные в MOCK MemoryManager, если это не сделано в его __init__
    # (В текущей заглушке данные добавляются в get_history для chat_id="test_chat_with_data")

    collector = FatigueCollector(memory_manager=mock_mm)

    test_chat_id = "test_chat_with_data"
    logger.info(f"\n--- Running FatigueCollector for chat_id: {test_chat_id} ---")
    fatigue_reports = collector.process_user_fatigue(test_chat_id)

    if fatigue_reports:
        logger.info(f"--- Generated {len(fatigue_reports)} reports ---")
        for report_model in fatigue_reports:
            try:
                print(report_model.model_dump_json(indent=2)) # Pydantic V2
            except AttributeError:
                print(report_model.json(indent=2)) # Pydantic V1

        # Тестирование сохранения в файл
        output_file = "fatigue_analysis_results.json"
        storage = LocalFileStorage(filepath=output_file)
        storage.save_batch(fatigue_reports)
        logger.info(f"Test results (should be) saved to {os.path.abspath(output_file)}")
    else:
        logger.info("No fatigue reports generated for the test chat_id.")

    logger.info(f"\n--- Running FatigueCollector for chat_id: empty_chat (expect no reports) ---")
    empty_reports = collector.process_user_fatigue("empty_chat")
    if not empty_reports:
        logger.info("Correctly generated no reports for 'empty_chat'.")

    # Можно добавить больше тестовых сценариев здесь
    # Например, сгенерировать более длинную историю сообщений
    # и проверить сегментацию на сессии.## Исправление и завершение `collector.py`

Проблема с `overwrite_file_with_block` и слишком длинным контентом была связана с тем, что предыдущий вывод этого инструмента был неполным (оборвался). Я перезаписываю файл `src/monitoring/fatigue_analyzer/collector.py` с полной версией кода, включающей исправления в импорте `MemoryManager` (чтобы он корректно находился или использовал заглушку), улучшенную логику сегментации сессий, логирование предупреждений и реализацию `LocalFileStorage`.
