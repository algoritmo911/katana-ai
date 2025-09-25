# bot/test_bot.py
import unittest
import json
from unittest.mock import MagicMock, patch

# Перед импортом бота и его модулей, нужно "замокать" токен
# Это важно, чтобы код в katana_bot.py не выбросил исключение при импорте
with patch('os.getenv') as mock_getenv:
    mock_getenv.return_value = '123456:ABC-DEF123456789'
    from bot import katana_bot
    from bot import commands as command_core
    from bot.nlp import parser as nlp_parser

class TestKatanaBot(unittest.TestCase):

    def setUp(self):
        """Настройка перед каждым тестом."""
        # Сбрасываем память пользователя перед каждым тестом
        katana_bot.user_memory = {}
        # Убедимся, что команды загружены
        command_core.load_commands()


    def test_01_command_loading(self):
        """Тест: ядро команд должно загружать все доступные модули команд."""
        metadata = command_core.get_all_commands_metadata()
        
        # Проверяем, что основные команды зарегистрированы
        expected_intents = [
            "get_weather", "clarify_city_for_weather", "tell_joke",
            "get_fact", "greeting", "goodbye", "get_time",
            "fallback_general", "fallback_clarification_needed",
            "fallback_after_clarification_fail"
        ]
        
        for intent in expected_intents:
            self.assertIn(intent, metadata, f"Команда для намерения '{intent}' не была загружена.")
            self.assertIsNotNone(command_core.get_handler(intent), f"Обработчик для '{intent}' не найден.")
        
        print(f"\n[Test 1 OK] Обнаружено {len(metadata)} команд.")


    def test_02_nlp_parser_simple_intents(self):
        """Тест: NLP-парсер должен правильно распознавать простые намерения."""
        test_cases = {
            "какая погода в москве": "get_weather",
            "расскажи анекдот": "tell_joke",
            "какой-нибудь факт": "get_fact",
            "привет": "greeting",
            "пока": "goodbye",
            "который час": "get_time",
        }

        for text, expected_intent in test_cases.items():
            with self.subTest(text=text):
                result = nlp_parser.analyze_text(text, {})
                self.assertGreater(len(result["intents"]), 0, "Намерение не было распознано.")
                self.assertEqual(result["intents"][0]["name"], expected_intent)

        print("[Test 2 OK] Простые намерения распознаются корректно.")


    def test_03_nlp_parser_entity_extraction(self):
        """Тест: NLP-парсер должен правильно извлекать сущности (город)."""
        text = "какая погода в городе Лондон"
        result = nlp_parser.analyze_text(text, {})
        self.assertIn("city", result["entities"])
        self.assertEqual(result["entities"]["city"], "Лондон")

        print("[Test 3 OK] Сущность 'город' извлекается корректно.")


    def test_04_e2e_greeting_and_joke(self):
        """Тест: полный цикл от сообщения до ответа (приветствие и анекдот)."""
        chat_id = 123
        user_text = "Привет! Расскажи анекдот"
        
        # Моделируем сообщение от пользователя
        mock_message = MagicMock()
        mock_message.chat.id = chat_id
        mock_message.text = user_text
        
        # Мокаем метод reply_to, чтобы перехватить ответ бота
        with patch.object(katana_bot.bot, 'reply_to') as mock_reply_to:
            katana_bot.handle_user_chat_message(mock_message)

            # Проверяем, что бот ответил
            mock_reply_to.assert_called_once()

            # Получаем аргументы, с которыми был вызван mock_reply_to
            args, _ = mock_reply_to.call_args
            sent_message = args[1] # Второй аргумент - это текст ответа

            # Ответ должен содержать приветствие и анекдот
            possible_greetings = ["Привет!", "Здравствуйте!", "Рад вас снова видеть!"]
            greeting_found = any(g in sent_message for g in possible_greetings)
            self.assertTrue(greeting_found, "Ответ не содержит ожидаемого приветствия.")

            # Проверяем, что в ответе есть часть одного из анекдотов
            joke_found = any(joke_part in sent_message for joke_part in ["Колобок", "программисты", "улитка"])
            self.assertTrue(joke_found, "Ответ не содержит ожидаемого анекдота.")

            print("[Test 4 OK] E2E тест на приветствие и анекдот пройден.")


    def test_05_e2e_weather_clarification_flow(self):
        """Тест: полный цикл диалога с уточнением погоды."""
        chat_id = 456

        # --- Шаг 1: Спрашиваем погоду без города ---
        user_text_1 = "какая погода"
        mock_message_1 = MagicMock()
        mock_message_1.chat.id = chat_id
        mock_message_1.text = user_text_1

        with patch.object(katana_bot.bot, 'reply_to') as mock_reply_to_1:
            katana_bot.handle_user_chat_message(mock_message_1)
            mock_reply_to_1.assert_called_once()
            args, _ = mock_reply_to_1.call_args
            sent_message_1 = args[1]
            self.assertIn("Для какого города", sent_message_1, "Бот не запросил уточнение города.")

        # --- Шаг 2: Уточняем город ---
        user_text_2 = "в Казани"
        mock_message_2 = MagicMock()
        mock_message_2.chat.id = chat_id
        mock_message_2.text = user_text_2

        with patch.object(katana_bot.bot, 'reply_to') as mock_reply_to_2:
            katana_bot.handle_user_chat_message(mock_message_2)
            mock_reply_to_2.assert_called_once()
            args, _ = mock_reply_to_2.call_args
            sent_message_2 = args[1]
            self.assertIn("Погода в городе Казани", sent_message_2, "Бот не дал погоду после уточнения.")

        print("[Test 5 OK] E2E тест на диалог с уточнением погоды пройден.")


if __name__ == '__main__':
    unittest.main()