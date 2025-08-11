import pytest
import os
import time
from dotenv import load_dotenv

# Загружаем переменные окружения, чтобы модули бота могли их использовать
load_dotenv()

# Убедимся, что мы в правильной директории для импорта
from bot import database
from bot.katana_bot import process_message_logic

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

    def test_full_conversation_flow(self, monkeypatch):
        """
        Полный интеграционный тест:
        1. Пользователь сообщает о планах.
        2. Проверяем, что планы корректно сохранились в БД.
        3. Пользователь задает вопрос о своих планах.
        4. Проверяем, что бот отвечает на основе сохраненной информации.
        """
        # Временно устанавливаем переменные окружения для этого теста
        monkeypatch.setenv("OPENAI_API_KEY", "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")
        monkeypatch.setenv("SUPABASE_KEY", "sb_secret_wtRSbhoCKkW53FAn2UzFpg_ED78K1LU")
        monkeypatch.setenv("SUPABASE_URL", "https://pmcaojgdrszvujvwzxrc.supabase.co")

        # --- Шаг 1: Пользователь сообщает о планах ---
        initial_statement = "Планирую на следующей неделе деловую поездку в Берлин, нужно будет встретиться с Ангелой Меркель."

        # Обрабатываем первое сообщение
        response1 = process_message_logic(TEST_CHAT_ID, initial_statement)

        # Даем небольшую паузу, чтобы данные успели записаться в БД
        time.sleep(2)

        # --- Шаг 2: Проверка состояния в БД ---
        history = database.get_recent_messages(TEST_CHAT_ID, limit=1)
        assert len(history) == 1, "Сообщение не было сохранено в БД"

        saved_message = history[0]
        metadata = saved_message.get("metadata", {})

        assert metadata, "Метаданные отсутствуют в сохраненном сообщении"

        # Проверяем намерение
        raw_intent = metadata.get("raw_intent", "").lower()
        assert "планирование" in raw_intent or "постановка задачи" in raw_intent, f"Ожидался интент 'планирование', но получен '{raw_intent}'"

        # Проверяем сущности
        raw_entities = metadata.get("raw_entities", [])
        entity_texts = {entity.get("text").lower() for entity in raw_entities}

        assert "берлин" in entity_texts, "Сущность 'Берлин' не найдена в метаданных"
        assert "ангелой меркель" in entity_texts, "Сущность 'Ангела Меркель' не найдена в метаданных"

        # --- Шаг 3: Пользователь задает уточняющий вопрос ---
        follow_up_question = "В какой город я собирался на следующей неделе?"

        # Обрабатываем второе сообщение
        response2 = process_message_logic(TEST_CHAT_ID, follow_up_question)

        # --- Шаг 4: Проверка ответа бота ---
        # TODO: Это утверждение должно измениться, когда будет реализована логика извлечения из памяти.
        # Пока что мы ожидаем, что бот не поймет и вернет fallback.
        # Когда логика будет готова, здесь будет `assert "берлин" in response2.lower()`

        print(f"Получен ответ на второй вопрос: {response2}")
        assert "берлин" in response2.lower(), f"Ожидалось, что в ответе будет 'Берлин', но получен ответ: '{response2}'"
