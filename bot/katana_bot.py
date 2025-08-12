import asyncio
import os
from datetime import datetime
from pathlib import Path
import json

import openai
import telebot
from bot.chat_history import ChatHistory
from bot.knowledge.graph_db import get_graph_db
from dotenv import load_dotenv
from telebot.async_telebot import AsyncTeleBot

# --- Инициализация ---

# Загружаем переменные окружения из .env файла
load_dotenv()

# Получаем токены и ключи из переменных окружения
TELEGRAM_TOKEN = os.getenv('KATANA_TELEGRAM_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if not TELEGRAM_TOKEN or ':' not in TELEGRAM_TOKEN:
    raise ValueError("❌ Неверный или отсутствующий токен Telegram. Установите переменную окружения KATANA_TELEGRAM_TOKEN.")

if not OPENAI_API_KEY or not OPENAI_API_KEY.startswith("sk-"):
    print("⚠️  Предупреждение: Ключ OpenAI API отсутствует или имеет неверный формат. Функциональность LLM будет отключена.")
    # raise ValueError("❌ Неверный или отсутствующий ключ OpenAI API. Установите переменную окружения OPENAI_API_KEY.")

bot = AsyncTeleBot(TELEGRAM_TOKEN)
openai_client = openai.AsyncClient(api_key=OPENAI_API_KEY)
graph = get_graph_db()

def log_local_bot_event(message):
    """Вывод лога события в консоль."""
    print(f"[BOT EVENT] {datetime.utcnow().isoformat()}: {message}")


# --- Новая логика мышления ---

# --- Конфигурация моделей ---
ENTITY_MODEL = os.getenv("OPENAI_ENTITY_MODEL", "gpt-4o-mini")
RESPONSE_MODEL = os.getenv("OPENAI_RESPONSE_MODEL", "gpt-4o")

async def get_entities_from_query(text: str) -> list[str]:
    """Извлекает ключевые сущности из текста с помощью LLM."""
    try:
        response = await openai_client.chat.completions.create(
            model=ENTITY_MODEL,
            messages=[
                {"role": "system", "content": "You are an entity extractor. Your goal is to extract the key nouns and proper names from the user's text. Return them as a JSON list of strings. For example, for the text 'What is Telepresence and who is Jules?', you should return {\"entities\": [\"Telepresence\", \"Jules\"]}. Do not return anything else, just the JSON object."},
                {"role": "user", "content": text}
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        entities_json_str = response.choices[0].message.content
        entities_dict = json.loads(entities_json_str)
        result = entities_dict.get("entities", [])
        log_local_bot_event(f"Извлеченные сущности: {result}")
        return result
    except Exception as e:
        log_local_bot_event(f"Ошибка при извлечении сущностей: {e}")
        return []

async def query_knowledge_graph(entities: list[str]) -> str:
    """Запрашивает граф знаний и форматирует результат в виде текста."""
    if not entities:
        return "В базе знаний не найдено релевантных фактов."

    all_facts = set()
    for entity in entities:
        # Ищем связи, где сущность является субъектом или объектом
        query = (
            "MATCH (n)-[r]-(m) "
            "WHERE n.name CONTAINS $entity "
            "RETURN n.name AS subject, type(r) AS verb, m.name AS object"
        )
        try:
            results = graph._execute_query(query, parameters={'entity': entity})
            for record in results:
                fact = f"({record['subject']}) -[{record['verb']}]-> ({record['object']})"
                all_facts.add(fact)
        except Exception as e:
            log_local_bot_event(f"Ошибка при запросе к графу для сущности '{entity}': {e}")

    if not all_facts:
        return "В базе знаний не найдено релевантных фактов."

    return "Факты из базы знаний:\n" + "\n".join(f"- {fact}" for fact in all_facts)


async def generate_response(user_text: str, chat_history: list, knowledge_facts: str) -> str:
    """Генерирует финальный ответ с помощью LLM, используя историю и факты."""

    system_prompt = """
Ты — Катана, продвинутый ИИ-ассистент. Твоя задача — давать четкие, полезные и основанные на фактах ответы.
Ты имеешь доступ к истории диалога и глобальной базе знаний.
Используй предоставленные факты из базы знаний, чтобы обогатить свой ответ.
Если факты противоречат истории диалога, отдавай предпочтение фактам как более достоверному источнику.
Отвечай на языке пользователя.
"""

    # Форматируем историю для промпта
    formatted_history = "\n".join([f"{msg['user']}: {msg['text']}" for msg in chat_history])

    prompt_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"""
Вот история нашего диалога:
---
{formatted_history}
---

Вот факты из глобальной базы знаний, которые могут быть релевантны:
---
{knowledge_facts}
---

Основываясь на всем вышесказанном, ответь на мой последний вопрос: {user_text}
"""
        }
    ]

    try:
        response = await openai_client.chat.completions.create(
            model=RESPONSE_MODEL,
            messages=prompt_messages,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        log_local_bot_event(f"Ошибка при генерации ответа LLM: {e}")
        return "Произошла ошибка при обработке вашего запроса. Попробуйте позже."


# --- Обработчики команд Telegram ---

@bot.message_handler(commands=['start'])
async def handle_start(message):
    """Ответ на /start"""
    response_text = "Привет! Я — Катана. Я могу отвечать на ваши вопросы, используя нашу общую базу знаний. Просто спросите меня о чем-нибудь."
    await bot.reply_to(message, response_text)
    log_local_bot_event(f"/start received from {message.chat.id}")
    history = ChatHistory(message.chat.id)
    history.add_message("user", "/start", message.date)
    history.add_message("bot", response_text, datetime.utcnow().isoformat())

@bot.message_handler(commands=['clear_history'])
async def handle_clear_history(message):
    """Очистка истории чата."""
    chat_id = message.chat.id
    history = ChatHistory(chat_id)
    history.clear_history()
    await bot.reply_to(message, "История этого чата очищена.")
    log_local_bot_event(f"Chat history cleared for {chat_id}")

@bot.message_handler(func=lambda message: True)
async def handle_message(message):
    """Главный обработчик входящих сообщений с новой логикой."""
    chat_id = message.chat.id
    user_text = message.text
    log_local_bot_event(f"Получено сообщение от {chat_id}: {user_text}")

    # 1. Сохраняем сообщение пользователя в историю
    history = ChatHistory(chat_id)
    history.add_message("user", user_text, message.date)

    # Ставим "typing..." статус
    await bot.send_chat_action(chat_id, 'typing')

    # 2. Извлекаем сущности из вопроса
    entities = await get_entities_from_query(user_text)

    # 3. Запрашиваем граф знаний
    knowledge_facts = await query_knowledge_graph(entities)
    log_local_bot_event(f"Полученные факты из графа:\n{knowledge_facts}")

    # 4. Получаем историю чата
    recent_history = history.get_history(limit=10)

    # 5. Генерируем ответ
    response_text = await generate_response(user_text, recent_history, knowledge_facts)

    # 6. Отправляем ответ и сохраняем его в историю
    await bot.reply_to(message, response_text)
    history.add_message("bot", response_text, datetime.utcnow().isoformat())
    log_local_bot_event(f"Отправлен ответ для {chat_id}: {response_text}")


if __name__ == '__main__':
    log_local_bot_event("Бот запускается...")
    # Убедимся, что цикл событий существует
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.run_until_complete(bot.polling())
    log_local_bot_event("Бот остановлен.")
