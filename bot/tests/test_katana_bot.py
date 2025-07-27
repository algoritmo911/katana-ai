# bot/tests/test_katana_bot.py
import unittest
from unittest.mock import patch, MagicMock, ANY
from bot import katana_bot

class TestKatanaBot(unittest.TestCase):

    def setUp(self):
        # Инициализируем memory_manager, если нужно
        katana_bot.init_dependencies()

    @patch('bot.katana_bot.bot.reply_to')
    @patch('bot.katana_bot.memory_manager')
    def test_handle_start(self, mock_memory_manager, mock_reply_to):
        # Создаем мок-сообщение с chat.id
        mock_message = MagicMock()
        mock_message.chat.id = 12345
        mock_message.text = "/start"

        # Вызываем функцию handle_start напрямую
        katana_bot.handle_start(mock_message)

        # Проверяем, что очистка истории была вызвана с правильным chat_id
        mock_memory_manager.clear_history.assert_called_once_with(str(mock_message.chat.id))

        # Проверяем, что bot.reply_to был вызван с сообщением приветствия
        mock_reply_to.assert_called_once()
        args, kwargs = mock_reply_to.call_args
        self.assertEqual(args[0], mock_message)
        self.assertIn("агент активирован", args[1])

        # Проверяем, что get_history не вызывается
        mock_memory_manager.get_history.assert_not_called()

        # Проверяем, что приветственное сообщение добавлено в историю
        mock_memory_manager.add_message_to_history.assert_called_once()
        add_msg_call_args = mock_memory_manager.add_message_to_history.call_args[0]
        # Первым аргументом — chat_id как строка
        self.assertEqual(add_msg_call_args[0], str(mock_message.chat.id))
        # Вторым — словарь с ролью assistant и текстом
        self.assertIsInstance(add_msg_call_args[1], dict)
        self.assertEqual(add_msg_call_args[1].get("role"), "assistant")
        self.assertIn("агент активирован", add_msg_call_args[1].get("content", ""))

    @patch('bot.katana_bot.get_katana_response', return_value="Test response")
    @patch('bot.katana_bot.bot.reply_to')
    @patch('bot.katana_bot.memory_manager')
    def test_handle_message_impl(self, mock_memory_manager, mock_reply_to, mock_get_katana_response):
        # Создаем мок-сообщение
        mock_message = MagicMock()
        mock_message.chat.id = 12345
        mock_message.text = "Hello"
        mock_message.from_user.username = "testuser"

        # Мокируем get_history
        mock_memory_manager.get_history.return_value = []

        # Вызываем handle_message_impl
        katana_bot.handle_message_impl(mock_message)

        # Проверяем, что get_history был вызван один раз
        mock_memory_manager.get_history.assert_called_once_with(str(mock_message.chat.id))

if __name__ == '__main__':
    unittest.main()
