import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Tuple
from collections import Counter

# Assuming MemoryManager is accessible, adjust import path if necessary
from src.memory.memory_manager import MemoryManager

logger = logging.getLogger(__name__)

# Initialize MemoryManager instance (consider how this is best managed - dependency injection?)
# For now, direct instantiation for simplicity in this module.
# This might need to be passed in or configured if Redis settings are not globally available.
try:
    # These would ideally come from a shared configuration
    import os
    # Changed from 'localhost' to '127.0.0.1' for redis_host default
    redis_host = os.getenv('REDIS_HOST', '127.0.0.1')
    redis_port = int(os.getenv('REDIS_PORT', '6379'))
    redis_password = os.getenv('REDIS_PASSWORD', None)
    redis_db = int(os.getenv('REDIS_DB', '0'))

    memory_manager = MemoryManager(
        host=redis_host,
        port=redis_port,
        db=redis_db,
        password=redis_password
    )
    if not memory_manager.redis_client:
        logger.error("Reporter: Failed to initialize MemoryManager due to Redis connection issue.")
        # Fallback or raise error - for now, functions might fail if memory_manager is not usable
        # To ensure memory_manager is None if redis_client is None after attempted init
        memory_manager = None
except Exception as e:
    logger.error(f"Reporter: Error initializing MemoryManager: {e}", exc_info=True)
    memory_manager = None # Ensure it's None if initialization fails

def get_notes_for_period(chat_id: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
    """
    Извлекает все сообщения пользователя из MemoryManager за указанный период.
    """
    if not memory_manager or not memory_manager.redis_client:
        logger.error(f"MemoryManager not available for chat_id {chat_id}")
        return []

    full_history = memory_manager.get_history(chat_id)
    notes_in_period = []

    for message in full_history:
        if message.get("role") == "user": # Consider only user messages as 'notes'
            timestamp_str = message.get("timestamp")
            if timestamp_str:
                try:
                    # Ensure timestamp is offset-aware for comparison
                    msg_timestamp = datetime.fromisoformat(timestamp_str)
                    if msg_timestamp.tzinfo is None:
                        msg_timestamp = msg_timestamp.replace(tzinfo=timezone.utc) # Assume UTC if not specified

                    if start_date <= msg_timestamp <= end_date:
                        notes_in_period.append(message)
                except ValueError:
                    logger.warning(f"Could not parse timestamp {timestamp_str} for message in chat {chat_id}")
    return notes_in_period

def analyze_notes(notes: List[Dict[str, Any]]) -> Tuple[List[str], List[str], Dict[str, Any]]:
    """
    Анализирует заметки для выделения ключевых инсайтов, горячих тем и статистики.
    (Простая эвристическая реализация)
    """
    if not notes:
        return [], [], {"total_notes": 0, "notes_by_day": {}}

    # Ключевые инсайты (просто первые несколько непустых заметок для примера)
    key_insights = [note['content'][:100] + "..." if len(note['content']) > 100 else note['content']
                    for note in notes if note.get('content')]
    key_insights = key_insights[:3] # Первые 3

    # Горячие темы (самые частые слова, более 3 букв, не стоп-слова)
    # Простой список стоп-слов для русского и английского
    stop_words = set([
        "и", "в", "во", "не", "что", "он", "на", "я", "с", "со", "как", "а", "то", "все", "она", "так", "его", "но", "да", "ты", "к", "у", "же",
        "вы", "за", "бы", "по", "только", "ее", "мне", "было", "вот", "от", "меня", "еще", "нет", "о", "из", "ему", "теперь", "когда", "даже",
        "ну", "вдруг", "ли", "если", "уже", "или", "ни", "быть", "был", "него", "до", "вас", "нибудь", "опять", "уж", "вам", "ведь", "там",
        "потом", "себя", "ничего", "ей", "может", "они", "тут", "где", "есть", "надо", "ней", "для", "мы", "тебя", "их", "чем", "была", "сам",
        "чтоб", "без", "будто", "чего", "раз", "тоже", "себе", "под", "будет", "ж", "тогда", "кто", "этот", "того", "потому", "этого", "какой",
        "совсем", "ним", "здесь", "этом", "один", "почти", "мой", "тем", "чтобы", "нее", "сейчас", "были", "куда", "зачем", "всех", "никогда",
        "можно", "при", "наконец", "два", "об", "другой", "хоть", "после", "над", "больше", "тот", "через", "эти", "нас", "про", "всего", "них",
        "какая", "много", "разве", "три", "эту", "моя", "впрочем", "хорошо", "свою", "этой", "перед", "иногда", "лучше", "чуть", "том", "нельзя",
        "такой", "им", "более", "всегда", "конечно", "всю", "между",
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "should",
        "can", "could", "may", "might", "must", "and", "but", "or", "nor", "for", "so", "yet", "if", "then", "else", "when", "where", "why",
        "how", "what", "which", "who", "whom", "whose", "this", "that", "these", "those", "i", "you", "he", "she", "it", "we", "they", "me",
        "him", "her", "us", "them", "my", "your", "his", "its", "our", "their", "mine", "yours", "hers", "ours", "theirs", "to", "of", "in",
        "on", "at", "by", "from", "with", "about", "against", "between", "into", "through", "during", "before", "after", "above", "below",
        "up", "down", "out", "over", "under", "again", "further", "then", "once", "here", "there", "all", "any", "both", "each", "few", "more",
        "most", "other", "some", "such", "no", "not", "only", "own", "same", "too", "very", "s", "t"
    ])

    word_counts = Counter()
    for note in notes:
        content = note.get('content', '')
        words = [word.strip('.,!?"\'`«»„“#$%^&*()[]{}<>:;').lower() for word in content.split()]
        for word in words:
            if len(word) > 3 and word not in stop_words:
                word_counts[word] += 1

    hot_topics = [word for word, count in word_counts.most_common(5)] # Топ-5 слов

    # Статистика активности
    total_notes = len(notes)
    notes_by_day = Counter()
    for note in notes:
        timestamp_str = note.get("timestamp")
        if timestamp_str:
            try:
                msg_timestamp = datetime.fromisoformat(timestamp_str)
                notes_by_day[msg_timestamp.strftime('%A')] += 1 # День недели
            except ValueError:
                pass

    activity_stats = {
        "total_notes": total_notes,
        "notes_by_day": dict(notes_by_day.most_common()) # Сортировка по частоте для наглядности
    }

    return key_insights, hot_topics, activity_stats

def format_report_markdown(chat_id: str, key_insights: List[str], hot_topics: List[str], activity_stats: Dict[str, Any], report_period_str: str) -> str:
    """
    Форматирует отчет в Markdown.
    """
    report_lines = [
        f"# Еженедельный отчет по заметкам ({report_period_str})\n"
        f"Для пользователя: `{chat_id}`\n"
    ]

    report_lines.append("## 🌟 Ключевые инсайты:\n")
    if key_insights:
        for i, insight in enumerate(key_insights):
            report_lines.append(f"{i+1}. {insight}")
    else:
        report_lines.append("_За прошедшую неделю инсайтов не найдено._\n")

    report_lines.append("\n## 🔥 Горячие темы (ключевые слова):\n")
    if hot_topics:
        report_lines.append(", ".join([f"`{topic}`" for topic in hot_topics]))
    else:
        report_lines.append("_Горячих тем не выявлено._\n")

    report_lines.append("\n## 📊 Статистика активности:\n")
    report_lines.append(f"- Всего заметок за неделю: **{activity_stats.get('total_notes', 0)}**")
    if activity_stats.get('notes_by_day'):
        report_lines.append("- Активность по дням:")
        for day, count in activity_stats['notes_by_day'].items():
            report_lines.append(f"  - {day}: {count} заметок")
    else:
        report_lines.append("_Данных по активности нет._\n")

    report_lines.append("\n---\n_Этот отчет сгенерирован автоматически._")

    return "\n".join(report_lines)

def generate_weekly_report(chat_id: str) -> str:
    """
    Генерирует еженедельный отчет для указанного chat_id.
    """
    if not memory_manager or not memory_manager.redis_client:
        logger.error(f"MemoryManager is not initialized or not connected. Cannot generate report for chat_id {chat_id}.")
        return "Ошибка: Сервис памяти недоступен. Невозможно сгенерировать отчет."

    now = datetime.now(timezone.utc)
    end_date = now
    start_date = now - timedelta(days=7)

    report_period_str = f"{start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}"
    logger.info(f"Generating weekly report for chat_id {chat_id} for period: {report_period_str}")

    notes = get_notes_for_period(chat_id, start_date, end_date)

    if not notes:
        logger.info(f"No notes found for chat_id {chat_id} in the last 7 days.")
        return f"За последнюю неделю ({report_period_str}) у вас не было заметок. Отчет не может быть сформирован."

    key_insights, hot_topics, activity_stats = analyze_notes(notes)

    report_markdown = format_report_markdown(chat_id, key_insights, hot_topics, activity_stats, report_period_str)

    logger.info(f"Successfully generated weekly report for chat_id {chat_id}. Total notes: {activity_stats['total_notes']}")
    return report_markdown

# Функция для будущей автоматической рассылки (пока не используется напрямую ботом)
# def send_weekly_digests(bot_instance):
# """
# Отправляет еженедельные дайджесты всем активным пользователям.
# (Требует механизма получения списка пользователей и экземпляра бота)
# """
#    logger.info("Attempting to send weekly digests...")
#    # Placeholder: Как получить список всех chat_id?
#    # Это может быть сложно без специального хранения списка пользователей.
#    # Вариант 1: Сканировать ключи Redis вида "chat_history:*" - может быть медленно.
#    # Вариант 2: Пользователи подписываются на дайджест, их chat_id сохраняются в отдельный список.
#
#    # Примерный псевдокод, если бы у нас был список chat_ids:
#    # all_chat_ids = get_all_subscribed_chat_ids() # hypothetical function
#    # for chat_id in all_chat_ids:
#    #     try:
#    #         report = generate_weekly_report(chat_id)
#    #         if bot_instance and hasattr(bot_instance, 'send_message'):
#    #             bot_instance.send_message(chat_id, report, parse_mode="Markdown")
#    #             logger.info(f"Sent weekly digest to {chat_id}")
#    #         else:
#    #             logger.error(f"Bot instance not provided or lacks send_message for chat_id {chat_id}")
#    #     except Exception as e:
#    #         logger.error(f"Failed to send weekly digest to {chat_id}: {e}", exc_info=True)
#    logger.warning("send_weekly_digests is not fully implemented yet.")


if __name__ == '__main__':
    # Пример использования (требует запущенного Redis с данными)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Для теста, предполагается, что REDIS_HOST и т.д. установлены в окружении
    # или MemoryManager сможет подключиться к localhost:6379

    # Убедитесь, что memory_manager инициализирован успешно
    if not memory_manager or not memory_manager.redis_client:
        logger.error("Memory Manager is not available. Exiting example.")
        exit(1)

    # Пример chat_id, для которого могут быть данные
    test_chat_id_report = "test_report_user_123"
    logger.info(f"--- Generating example weekly report for chat_id: {test_chat_id_report} ---")

    # Добавим немного тестовых данных, если их нет
    # В реальном сценарии данные должны быть добавлены через бота
    now_ts = datetime.now(timezone.utc)
    if not memory_manager.get_history(test_chat_id_report):
        logger.info(f"Adding some sample data for {test_chat_id_report} for testing purposes...")
        messages_to_add = [
            {"role": "user", "content": "Первая заметка о проекте Катана. Нужно не забыть проанализировать результаты.", "timestamp": (now_ts - timedelta(days=6)).isoformat()},
            {"role": "assistant", "content": "Понял.", "timestamp": (now_ts - timedelta(days=6, hours=-1)).isoformat()},
            {"role": "user", "content": "Обсудили важный момент по поводу NLP моделей. OpenAI или Anthropic?", "timestamp": (now_ts - timedelta(days=5)).isoformat()},
            {"role": "user", "content": "Статистика показывает рост активности пользователей.", "timestamp": (now_ts - timedelta(days=4)).isoformat()},
            {"role": "user", "content": "Ключевой инсайт: пользователи предпочитают короткие и ясные ответы.", "timestamp": (now_ts - timedelta(days=3)).isoformat()},
            {"role": "user", "content": "Горячая тема этой недели - производительность бота.", "timestamp": (now_ts - timedelta(days=2)).isoformat()},
            {"role": "user", "content": "Еще одна заметка про производительность и оптимизацию.", "timestamp": (now_ts - timedelta(days=1)).isoformat()},
            {"role": "user", "content": "Финальная мысль на сегодня: нужно подготовить еженедельный отчет.", "timestamp": (now_ts - timedelta(hours=5)).isoformat()},
        ]
        for msg in messages_to_add:
            memory_manager.add_message_to_history(test_chat_id_report, msg)
        logger.info(f"Added {len(messages_to_add)} sample messages for {test_chat_id_report}.")

    report = generate_weekly_report(test_chat_id_report)
    print("\n--- Сгенерированный отчет: ---\n")
    print(report)

    logger.info(f"--- Example report generation finished for chat_id: {test_chat_id_report} ---")

    # Пример для пользователя без заметок
    test_empty_chat_id = "test_empty_user_456"
    memory_manager.clear_history(test_empty_chat_id) # Убедимся, что истории нет
    logger.info(f"--- Generating example weekly report for chat_id with no notes: {test_empty_chat_id} ---")
    empty_report = generate_weekly_report(test_empty_chat_id)
    print("\n--- Отчет для пользователя без заметок: ---\n")
    print(empty_report)
    logger.info(f"--- Example report generation finished for chat_id: {test_empty_chat_id} ---")
