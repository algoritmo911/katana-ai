import os
from supabase import create_client, Client
from dotenv import load_dotenv
import functools

# Глобальная переменная для хранения инстанса клиента
_supabase_client = None

@functools.lru_cache(maxsize=1)
def get_supabase_client():
    """
    Инициализирует и возвращает синглтон-экземпляр клиента Supabase.
    Использует кэширование для предотвращения повторной инициализации.
    """
    global _supabase_client
    if _supabase_client:
        return _supabase_client

    load_dotenv()

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        raise ValueError("Supabase URL или Key не найдены в переменных окружения.")

    _supabase_client = create_client(url, key)
    return _supabase_client

def save_message(chat_id: int, user_text: str, bot_response: str, metadata: dict):
    """
    Сохраняет сообщение пользователя, ответ бота и метаданные в базу данных Supabase.
    """
    try:
        supabase = get_supabase_client()
        # Предполагаем, что таблица называется 'messages'
        data, count = supabase.table('messages').insert({
            'chat_id': chat_id,
            'user_text': user_text,
            'bot_response': bot_response,
            'metadata': metadata
        }).execute()

        print(f"DB: Сообщение для chat_id {chat_id} успешно сохранено.")
        return data
    except (ValueError, Exception) as e:
        print(f"ОШИБКА DB: Не удалось сохранить сообщение для chat_id {chat_id}. Ошибка: {e}")
        return None

def get_recent_messages(chat_id: int, limit: int = 10):
    """
    Извлекает последние сообщения для указанного чата.
    """
    try:
        supabase = get_supabase_client()
        # Извлекаем последние 'limit' сообщений, отсортированных по времени создания
        data, count = supabase.table('messages')\
            .select('*')\
            .eq('chat_id', chat_id)\
            .order('created_at', desc=True)\
            .limit(limit)\
            .execute()

        # Ответ приходит в виде (data, count), нам нужен data
        # и он будет в виде списка словарей.
        # Переворачиваем список, чтобы сообщения были в хронологическом порядке
        return list(reversed(data[1])) if data and len(data) > 1 else []

    except (ValueError, Exception) as e:
        print(f"ОШИБКА DB: Не удалось получить историю для chat_id {chat_id}. Ошибка: {e}")
        return []

def delete_messages_for_chat(chat_id: int):
    """
    Удаляет все сообщения для указанного chat_id. ИСПОЛЬЗОВАТЬ ТОЛЬКО В ТЕСТАХ.
    """
    try:
        supabase = get_supabase_client()
        data, count = supabase.table('messages').delete().eq('chat_id', chat_id).execute()
        print(f"DB_TEST: Удалено {count} сообщений для chat_id {chat_id}.")
        return count
    except (ValueError, Exception) as e:
        print(f"ОШИБКА DB_TEST: Не удалось удалить сообщения для chat_id {chat_id}. Ошибка: {e}")
        return None

def search_messages_by_keywords(chat_id: int, keywords: list[str]):
    """
    Ищет в истории сообщения, метаданные которых содержат ключевые слова.
    """
    if not keywords:
        return []

    try:
        supabase = get_supabase_client()
        # Используем .or_ для поиска по любому из ключевых слов в массиве keywords внутри JSONB
        # 'cs' означает 'contains'. Строка для запроса должна быть вида '["word1"]'
        # Поэтому мы оборачиваем слово в кавычки и квадратные скобки.
        filter_query = ",".join([f'metadata->keywords.cs.["{kw}"]' for kw in keywords])

        data, count = supabase.table('messages')\
            .select('user_text, bot_response, metadata, created_at')\
            .eq('chat_id', chat_id)\
            .or_(filter_query)\
            .order('created_at', desc=True)\
            .limit(5)\
            .execute()

        return list(reversed(data[1])) if data and len(data) > 1 else []
    except (ValueError, Exception) as e:
        print(f"ОШИБКА DB: Не удалось выполнить поиск по ключевым словам для chat_id {chat_id}. Ошибка: {e}")
        return []

def get_all_documents():
    """
    Извлекает все документы из таблицы documents.
    """
    try:
        supabase = get_supabase_client()
        data, count = supabase.table('documents').select('id, source, content, embedding').execute()
        return data[1] if data and len(data) > 1 else []
    except (ValueError, Exception) as e:
        print(f"ОШИБКА DB: Не удалось извлечь все документы. Ошибка: {e}")
        return []

# def save_initiative_proposal(initiative_id: str, title: str, proposal_data: dict):
#     """
#     Сохраняет предложенную инициативу в таблицу 'initiatives'.
#     ВРЕМЕННО ОТКЛЮЧЕНО ИЗ-ЗА ПРОБЛЕМЫ СЕРИАЛИЗАЦИИ В SUPABASE-PY.
#     """
#     try:
#         supabase = get_supabase_client()
#         data, count = supabase.table('initiatives').insert({
#             'initiative_id': initiative_id,
#             'title': title,
#             'status': 'PENDING_APPROVAL', # Начальный статус после анализа
#             'proposal_data': proposal_data
#         }).execute()

#         print(f"DB: Инициатива '{title}' сохранена со статусом PENDING_APPROVAL.")
#         return data
#     except Exception as e:
#         print(f"ОШИБКА DB: Не удалось сохранить инициативу '{title}'. Ошибка: {e}")
#         return None

def update_initiative_status(initiative_id: str, new_status: str):
    """Обновляет статус указанной инициативы."""
    try:
        supabase = get_supabase_client()
        data, count = supabase.table('initiatives').update({'status': new_status}).eq('initiative_id', initiative_id).execute()
        print(f"DB: Статус инициативы '{initiative_id}' обновлен на '{new_status}'.")
        return data
    except Exception as e:
        print(f"ОШИБКА DB: Не удалось обновить статус для '{initiative_id}'. Ошибка: {e}")
        return None

def get_global_kill_switch_status() -> bool:
    """Проверяет состояние 'красного телефона'. Возвращает True, если авто-режим включен."""
    try:
        supabase = get_supabase_client()
        data, count = supabase.table('global_config').select('value').eq('key', 'AUTONOMOUS_MODE_ENABLED').execute()
        if data and len(data) > 1 and data[1]:
            return data[1][0]['value']
        # По умолчанию, если ключ не найден, считаем, что режим выключен (безопасность)
        return False
    except Exception as e:
        print(f"ОШИБКА DB: Не удалось получить статус 'красного телефона'. Ошибка: {e}")
        return False


# Пример использования (для ручного тестирования)
if __name__ == '__main__':
    if not supabase:
        print("Клиент Supabase не был создан. Выполнение примера остановлено.")
    else:
        # Пример сохранения
        print("\n--- Тест сохранения сообщения ---")
        test_meta = {'intent': 'test', 'sentiment': 'neutral'}
        save_message(12345, "Тестовое сообщение", "Тестовый ответ", test_meta)

        # Пример получения
        print("\n--- Тест получения сообщений ---")
        messages = get_recent_messages(12345)
        if messages:
            print(f"Найдено {len(messages)} сообщений для chat_id 12345.")
            for msg in messages:
                print(f"- {msg['user_text']} -> {msg['bot_response']} (Meta: {msg['metadata']})")
        else:
            print("Сообщений для chat_id 12345 не найдено.")
