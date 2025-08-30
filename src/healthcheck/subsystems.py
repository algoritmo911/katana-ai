import os
import openai
import requests

def check_openai_status():
    """
    Проверяет статус OpenAI API, пытаясь получить список моделей.
    Предполагает, что ключ API OPENAI_API_KEY установлен в переменных окружения.
    """
    try:
        # Убедимся, что ключ API установлен
        if not os.getenv("OPENAI_API_KEY"):
            return "СБОЙ", "Ключ OPENAI_API_KEY не найден"

        client = openai.OpenAI()
        client.models.list()
        return "ОНЛАЙН", "Сервис доступен"
    except Exception as e:
        return "СБОЙ", str(e)

def check_supabase_status():
    """
    Проверяет статус Supabase, отправляя запрос к его REST API.
    Предполагает, что SUPABASE_URL и SUPABASE_KEY установлены в переменных окружения.
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY") # Часто используется anon ключ для таких проверок

    if not supabase_url or not supabase_key:
        return "СБОЙ", "Переменные окружения SUPABASE_URL или SUPABASE_ANON_KEY не найдены"

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}"
    }

    try:
        # Проверяем базовый эндпоинт, который должен быть всегда доступен
        response = requests.get(f"{supabase_url}/rest/v1/", headers=headers, timeout=10)
        if response.status_code == 200:
            return "ОНЛАЙН", "Сервис доступен"
        else:
            return "СБОЙ", f"Код ответа: {response.status_code}"
    except requests.exceptions.RequestException as e:
        return "СБОЙ", str(e)

def check_n8n_status():
    """
    Проверяет статус n8n, обращаясь к его эндпоинту /healthz.
    Предполагает, что N8N_URL установлен в переменных окружения.
    """
    n8n_url = os.getenv("N8N_URL")

    if not n8n_url:
        return "СБОЙ", "Переменная окружения N8N_URL не найдена"

    try:
        # Стандартный эндпоинт для проверки здоровья многих сервисов
        response = requests.get(f"{n8n_url.rstrip('/')}/healthz", timeout=10)
        if response.status_code == 200:
            return "ОНЛАЙН", "Сервис доступен"
        else:
            return "СБОЙ", f"Код ответа: {response.status_code}"
    except requests.exceptions.RequestException as e:
        return "СБОЙ", str(e)
