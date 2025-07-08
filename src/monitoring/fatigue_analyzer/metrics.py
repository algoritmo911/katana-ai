import math
from datetime import datetime, timedelta, timezone
from typing import List, Tuple, Optional, Any
import statistics # For median and stdev

# schemas.py должен быть в том же пакете (src/monitoring/fatigue_analyzer)
from .schemas import MessageInput

# Константы для ролей, можно вынести в schemas или config
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant" # или "bot", "ai", в зависимости от MemoryManager

DEFAULT_BOT_ERROR_KEYWORDS = ["error", "failed", "failure", "problem", "issue", "ошибка", "сбой", "проблема", "не удалось"]
DEFAULT_USER_SWITCH_COMMANDS = ["mind_clearing", "cancel", "reset", "/mind_clearing", "/cancel", "/reset"]


def get_user_messages(messages: List[MessageInput]) -> List[MessageInput]:
    """Фильтрует сообщения, оставляя только сообщения пользователя."""
    return [msg for msg in messages if msg.role == ROLE_USER]

def get_assistant_messages(messages: List[MessageInput]) -> List[MessageInput]:
    """Фильтрует сообщения, оставляя только сообщения ассистента."""
    return [msg for msg in messages if msg.role == ROLE_ASSISTANT]


def calculate_command_frequency(
    messages: List[MessageInput],
    interval_minutes: int,
    current_time: Optional[datetime] = None
) -> int:
    """
    Подсчитывает количество сообщений пользователя за указанный интервал времени до current_time.
    Если current_time не указан, используется время последнего сообщения в списке.
    """
    if not messages:
        return 0

    # current_time для отсечки; если не задан, берем время последнего сообщения или текущее время UTC
    if current_time is None:
        # Проверяем, есть ли сообщения, чтобы взять timestamp последнего
        user_messages_for_ts = get_user_messages(messages) # Фильтруем пользовательские для определения последнего
        if user_messages_for_ts:
             current_time = user_messages_for_ts[-1].timestamp # Время последнего сообщения пользователя
        else: # Если нет сообщений пользователя (или вообще сообщений), но current_time не передан
            # В этом случае частота будет 0, но для корректности интервала лучше иметь current_time
            # Однако, если messages пуст, мы уже вышли. Если есть только сообщения бота,
            # то current_time от них не имеет смысла для частоты команд пользователя.
            # Логичнее, если current_time не задан и нет сообщений пользователя, вернуть 0,
            # что и произойдет, т.к. user_messages будет пуст.
            # Для безопасности, если current_time все еще None, можно взять now_utc,
            # но это может быть не то, что ожидает вызывающий код, если он передает исторические данные.
            # Оставим current_time как есть, фильтрация по user_messages далее обработает это.
            pass


    # Если current_time все еще не определен (например, messages содержат только ботовские сообщения)
    # или если он был определен, но без таймзоны
    if current_time is None: # Должно быть обработано ранее, но для страховки
        effective_current_time = datetime.now(timezone.utc)
    else:
        effective_current_time = current_time
        if effective_current_time.tzinfo is None:
            effective_current_time = effective_current_time.replace(tzinfo=timezone.utc)

    interval_start_time = effective_current_time - timedelta(minutes=interval_minutes)

    user_messages = get_user_messages(messages)

    count = 0
    for msg in user_messages:
        msg_ts = msg.timestamp
        if msg_ts.tzinfo is None:
            msg_ts = msg_ts.replace(tzinfo=timezone.utc)

        if interval_start_time <= msg_ts <= effective_current_time:
            count += 1
    return count


def calculate_reaction_times(
    messages: List[MessageInput]
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Рассчитывает среднее, медианное и стандартное отклонение времени реакции пользователя.
    Время реакции = время между сообщением ассистента и следующим сообщением пользователя.
    Возвращает (среднее, медиана, std_dev) в секундах.
    """
    reaction_times_sec: List[float] = []

    for i in range(len(messages) - 1):
        current_msg = messages[i]
        next_msg = messages[i+1]

        if current_msg.role == ROLE_ASSISTANT and next_msg.role == ROLE_USER:
            current_ts = current_msg.timestamp
            if current_ts.tzinfo is None:
                current_ts = current_ts.replace(tzinfo=timezone.utc)

            next_ts = next_msg.timestamp
            if next_ts.tzinfo is None:
                next_ts = next_ts.replace(tzinfo=timezone.utc)

            time_diff_seconds = (next_ts - current_ts).total_seconds()
            if time_diff_seconds >= 0:
                reaction_times_sec.append(time_diff_seconds)

    if not reaction_times_sec:
        return None, None, None

    avg_reaction_time = statistics.mean(reaction_times_sec)
    median_reaction_time = statistics.median(reaction_times_sec)
    std_dev_reaction_time = statistics.stdev(reaction_times_sec) if len(reaction_times_sec) > 1 else None

    return avg_reaction_time, median_reaction_time, std_dev_reaction_time


def calculate_error_rate(
    messages: List[MessageInput],
    bot_error_keywords: Optional[List[str]] = None,
    user_command_keywords: Optional[List[str]] = None
) -> float:
    if not messages:
        return 0.0

    if bot_error_keywords is None:
        bot_error_keywords = DEFAULT_BOT_ERROR_KEYWORDS
    # user_command_keywords на данный момент не используется для error_rate, но параметр оставлен

    error_indicators_count = 0
    assistant_messages = get_assistant_messages(messages)

    if not assistant_messages: # Если нет сообщений ассистента, то и ошибок от него нет
        return 0.0

    for msg in assistant_messages:
        if isinstance(msg.content, str):
            for keyword in bot_error_keywords:
                if keyword.lower() in msg.content.lower():
                    error_indicators_count += 1
                    break
    return error_indicators_count / len(assistant_messages)


def calculate_session_duration(
    session_start_time: datetime,
    session_end_time: datetime
) -> float:
    if session_start_time.tzinfo is None:
        session_start_time = session_start_time.replace(tzinfo=timezone.utc)
    if session_end_time.tzinfo is None:
        session_end_time = session_end_time.replace(tzinfo=timezone.utc)

    duration_seconds = (session_end_time - session_start_time).total_seconds()
    return duration_seconds / 60.0


def calculate_context_switch_frequency(
    messages: List[MessageInput],
    switch_commands: Optional[List[str]] = None
) -> int:
    if switch_commands is None:
        switch_commands = DEFAULT_USER_SWITCH_COMMANDS

    user_messages = get_user_messages(messages)
    switch_count = 0

    for msg in user_messages:
        if isinstance(msg.content, str):
            normalized_content = msg.content.lower().strip()
            for cmd in switch_commands:
                if normalized_content == cmd.lower():
                    switch_count += 1
                    break
    return switch_count


def calculate_user_bot_ratio(
    messages: List[MessageInput],
    warning_threshold: float = 2.5,
    min_messages_for_warning: int = 5
) -> Tuple[Optional[float], bool]:
    user_messages_count = len(get_user_messages(messages))
    assistant_messages_count = len(get_assistant_messages(messages))

    ratio: Optional[float]
    if assistant_messages_count == 0:
        ratio = float('inf') if user_messages_count > 0 else None
    else:
        ratio = user_messages_count / assistant_messages_count

    warning = False
    if ratio is not None and ratio > warning_threshold and (user_messages_count + assistant_messages_count) >= min_messages_for_warning:
        warning = True

    return ratio, warning


def calculate_fatigue_score(
    metrics: dict,
    weights: Optional[dict] = None
) -> Optional[float]:
    if weights is None:
        weights = {
            "avg_reaction_time_norm": 0.25,
            "error_rate_norm": 0.35,
            "context_switches_norm": 0.20,
            "user_bot_ratio_norm": 0.10,
            "command_frequency_10m_norm": 0.10
        }

    normalized_scores: Dict[str, float] = {}

    avg_rt = metrics.get("average_reaction_time_sec")
    if avg_rt is not None:
        if avg_rt <= 5: normalized_scores["avg_reaction_time_norm"] = 0.0
        elif avg_rt <= 30: normalized_scores["avg_reaction_time_norm"] = (avg_rt - 5) / (30 - 5)
        else: normalized_scores["avg_reaction_time_norm"] = 1.0

    error_rate = metrics.get("error_rate")
    if error_rate is not None:
        normalized_scores["error_rate_norm"] = min(max(error_rate, 0.0), 1.0) # Убедимся, что в [0,1]

    cs = metrics.get("context_switches")
    if cs is not None:
        if cs == 0: normalized_scores["context_switches_norm"] = 0.0
        elif cs == 1: normalized_scores["context_switches_norm"] = 0.3
        elif cs == 2: normalized_scores["context_switches_norm"] = 0.6
        else: normalized_scores["context_switches_norm"] = 1.0

    ub_ratio = metrics.get("user_bot_message_ratio")
    if ub_ratio is not None and not math.isinf(ub_ratio) and not math.isnan(ub_ratio): # Игнорируем inf/nan
        if ub_ratio < 1.5: normalized_scores["user_bot_ratio_norm"] = 0.0
        elif ub_ratio <= 3.0: normalized_scores["user_bot_ratio_norm"] = (ub_ratio - 1.5) / (3.0 - 1.5)
        else: normalized_scores["user_bot_ratio_norm"] = 1.0

    cmd_freq = metrics.get("command_frequency_10m")
    if cmd_freq is not None:
        if cmd_freq <= 5: normalized_scores["command_frequency_10m_norm"] = 0.0
        elif cmd_freq <= 15: normalized_scores["command_frequency_10m_norm"] = (cmd_freq - 5) / (15 - 5)
        else: normalized_scores["command_frequency_10m_norm"] = 1.0

    final_score = 0.0
    total_weight = 0.0

    if not normalized_scores: # Если ни одна метрика не была нормализована
        return None

    for key, norm_value in normalized_scores.items():
        if key in weights:
            final_score += norm_value * weights[key]
            total_weight += weights[key]

    if total_weight == 0:
        return None # Не удалось посчитать на основе имеющихся метрик и весов

    return min(max(final_score / total_weight, 0.0), 1.0)


if __name__ == "__main__":
    # Примеры для тестирования функций (оставлены для возможности прямого запуска metrics.py)
    now_utc_main = datetime.now(timezone.utc)
    messages_fixture_main: List[MessageInput] = [
        MessageInput(role=ROLE_USER, content="Привет", timestamp=now_utc_main - timedelta(minutes=60)),
        MessageInput(role=ROLE_ASSISTANT, content="Привет! Чем могу помочь?", timestamp=now_utc_main - timedelta(minutes=59, seconds=30)),
        MessageInput(role=ROLE_USER, content="Расскажи анекдот", timestamp=now_utc_main - timedelta(minutes=59)),
        MessageInput(role=ROLE_ASSISTANT, content="Колобок повесился.", timestamp=now_utc_main - timedelta(minutes=58)),
        MessageInput(role=ROLE_USER, content="Смешно. А другой?", timestamp=now_utc_main - timedelta(minutes=50)),
        MessageInput(role=ROLE_ASSISTANT, content="Почему курица перешла дорогу? Чтобы попасть на другую сторону!", timestamp=now_utc_main - timedelta(minutes=49)),
        MessageInput(role=ROLE_USER, content="/mind_clearing", timestamp=now_utc_main - timedelta(minutes=40)),
        MessageInput(role=ROLE_ASSISTANT, content="Контекст очищен.", timestamp=now_utc_main - timedelta(minutes=39)),
        MessageInput(role=ROLE_USER, content="Какая погода?", timestamp=now_utc_main - timedelta(minutes=8)),
        MessageInput(role=ROLE_ASSISTANT, content="Солнечно, +25C.", timestamp=now_utc_main - timedelta(minutes=7)),
        MessageInput(role=ROLE_USER, content="Спасибо", timestamp=now_utc_main - timedelta(minutes=6)),
        MessageInput(role=ROLE_ASSISTANT, content="Пожалуйста!", timestamp=now_utc_main - timedelta(minutes=5)),
        MessageInput(role=ROLE_USER, content="Что-то пошло не так, ошибка!", timestamp=now_utc_main - timedelta(minutes=4)),
        MessageInput(role=ROLE_ASSISTANT, content="Произошла ошибка при обработке вашего запроса.", timestamp=now_utc_main - timedelta(minutes=3)),
    ]

    print(f"--- Testing metrics.py directly (current time: {now_utc_main.isoformat()}) ---")
    print(f"Commands in last 10 mins: {calculate_command_frequency(messages_fixture_main, 10, current_time=now_utc_main)}")
    avg_rt_main, med_rt_main, std_rt_main = calculate_reaction_times(messages_fixture_main)
    print(f"Avg Reaction Time: {avg_rt_main:.2f}s" if avg_rt_main is not None else "N/A")
    error_rate_val_main = calculate_error_rate(messages_fixture_main)
    print(f"Error Rate: {error_rate_val_main:.2%}")
    # ... и так далее для других функций, если нужно ...
    example_metrics_dict_main = {
        "average_reaction_time_sec": avg_rt_main, "error_rate": error_rate_val_main,
        "context_switches": calculate_context_switch_frequency(messages_fixture_main),
        "user_bot_message_ratio": calculate_user_bot_ratio(messages_fixture_main)[0],
        "command_frequency_10m": calculate_command_frequency(messages_fixture_main, 10, current_time=now_utc_main)
    }
    fatigue_score_val_main = calculate_fatigue_score(example_metrics_dict_main)
    print(f"Calculated Fatigue Score: {fatigue_score_val_main:.2f}" if fatigue_score_val_main is not None else "N/A")
