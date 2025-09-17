import pytest
import os
import time
from dotenv import load_dotenv

# Загружаем переменные окружения, чтобы модули бота могли их использовать
load_dotenv()

# Убедимся, что мы в правильной директории для импорта
from bot import database
from bot.katana_bot import KatanaBot

# Пропускаем тесты, если не заданы ключи API, чтобы не падать в CI/CD
# Эти маркеры требуют наличия pytest.ini с описанием маркеров
requires_api_keys = pytest.mark.skipif(
    not (os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY") and os.getenv("OPENAI_API_KEY")),
    reason="Тест требует наличия реальных SUPABASE_URL, SUPABASE_KEY и OPENAI_API_KEY в .env"
)

TEST_CHAT_ID = 123456789 # Уникальный ID для тестового чата

@requires_api_keys
@pytest.mark.integration
class TestSemanticUnderstanding:

    def setup_method(self):
        """Настройка перед каждым тестом: очистка истории сообщений в БД."""
        print(f"Очистка БД для chat_id: {TEST_CHAT_ID}")
        database.delete_messages_for_chat(TEST_CHAT_ID)

    def teardown_method(self):
        """Очистка после каждого теста."""
        print(f"Очистка БД для chat_id: {TEST_CHAT_ID}")
        database.delete_messages_for_chat(TEST_CHAT_ID)

    def test_full_conversation_flow(self):
        """
        Полный интеграционный тест:
        1. Пользователь сообщает о планах.
        2. Проверяем, что планы корректно сохранились в БД.
        3. Пользователь задает вопрос о своих планах.
        4. Проверяем, что бот отвечает на основе сохраненной информации.
        """
        # Создаем экземпляр бота для теста
        bot = KatanaBot(chat_id=TEST_CHAT_ID)

        # --- Шаг 1: Пользователь сообщает о планах ---
        initial_statement = "Планирую на следующей неделе деловую поездку в Берлин, нужно будет встретиться с Ангелой Меркель."

        # Обрабатываем первое сообщение
        response1 = bot.process_chat_message(initial_statement)

        # Даем небольшую паузу, чтобы данные успели записаться в БД
        time.sleep(5) # Увеличим паузу для надежности

        # --- Шаг 2: Проверка состояния в БД ---
        history = database.get_recent_messages(TEST_CHAT_ID, limit=1)
        assert len(history) == 1, "Сообщение не было сохранено в БД"

        saved_message = history[0]
        # В новой структуре метаданные хранятся в поле `metadata`, а не `raw_intent`
        metadata = saved_message.get("metadata", {}).get("nlp_metadata", {})

        assert metadata, "Метаданные NLP отсутствуют в сохраненном сообщении"

        # Проверяем намерение
        intent = metadata.get("intent", "").lower()
        assert "plan" in intent, f"Ожидался интент 'plan', но получен '{intent}'"

        # Проверяем сущности
        entities = metadata.get("entities", [])
        entity_texts = {entity.get("text").lower() for entity in entities}

        assert "берлин" in entity_texts, "Сущность 'Берлин' не найдена в метаданных"
        assert "ангелой меркель" in entity_texts, "Сущность 'Ангела Меркель' не найдена в метаданных"

        # --- Шаг 3: Пользователь задает уточняющий вопрос ---
        follow_up_question = "В какой город я собирался на следующей неделе?"

        # Обрабатываем второе сообщение
        response2 = bot.process_chat_message(follow_up_question)

        # --- Шаг 4: Проверка ответа бота ---
        print(f"Получен ответ на второй вопрос: {response2}")
        assert "берлин" in response2.lower(), f"Ожидалось, что в ответе будет 'Берлин', но получен ответ: '{response2}'"
