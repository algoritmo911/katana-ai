import os
import openai
import requests
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Константы для статусов
STATUS_ONLINE = "ОНЛАЙН"
STATUS_OFFLINE = "СБОЙ"
COLOR_GREEN = "green"
COLOR_RED = "red"

def check_openai():
    """
    Проверяет доступность API OpenAI.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return STATUS_OFFLINE, COLOR_RED, "API ключ OpenAI не найден"

    client = openai.OpenAI(api_key=api_key)
    try:
        # Делаем простой и быстрый запрос, например, список моделей
        client.models.list()
        return STATUS_ONLINE, COLOR_GREEN, "Сервис доступен"
    except Exception as e:
        return STATUS_OFFLINE, COLOR_RED, f"Ошибка: {e}"

def check_supabase():
    """
    Проверяет доступность Supabase.
    Пингует health-check эндпоинт.
    """
    url = os.getenv("SUPABASE_URL")
    anon_key = os.getenv("SUPABASE_ANON_KEY")

    if not url or not anon_key:
        return STATUS_OFFLINE, COLOR_RED, "URL или ключ Supabase не найдены"

    # Обычно у Supabase есть health-check эндпоинт по адресу /rest/v1/?
    # Это базовый пинг, который не требует особых прав
    health_check_url = f"{url}/rest/v1/"
    headers = {
        "apikey": anon_key,
        "Authorization": f"Bearer {anon_key}",
    }
    try:
        response = requests.get(health_check_url, headers=headers, timeout=5)
        # Supabase health check должен вернуть 200 OK
        if response.status_code == 200:
            return STATUS_ONLINE, COLOR_GREEN, "Сервис доступен"
        else:
            return STATUS_OFFLINE, COLOR_RED, f"Статус: {response.status_code}"
    except requests.exceptions.RequestException as e:
        return STATUS_OFFLINE, COLOR_RED, f"Ошибка: {e}"


def check_n8n():
    """
    Проверяет доступность n8n.
    Пингует корневой URL или специальный health-check эндпоинт.
    """
    url = os.getenv("N8N_URL")
    if not url:
        return STATUS_OFFLINE, COLOR_RED, "URL n8n не найден"

    # У n8n может быть /healthz эндпоинт
    health_check_url = f"{url.rstrip('/')}/healthz"
    try:
        response = requests.get(health_check_url, timeout=5)
        if response.status_code == 200:
            return STATUS_ONLINE, COLOR_GREEN, "Сервис доступен"
        else:
            # Попробуем просто корневой URL, если /healthz не сработал
            response_root = requests.get(url, timeout=5)
            if response_root.status_code == 200:
                 return STATUS_ONLINE, COLOR_GREEN, "Сервис доступен (корневой URL)"
            return STATUS_OFFLINE, COLOR_RED, f"Статус: {response.status_code}"
    except requests.exceptions.RequestException as e:
        return STATUS_OFFLINE, COLOR_RED, f"Ошибка: {e}"
