import unittest
from unittest.mock import MagicMock, patch, call
import json
from pathlib import Path
import shutil # For robust directory removal

# Assuming bot.py is in the same directory or accessible in PYTHONPATH
# import bot # Старый импорт, который может вызывать проблемы при тестировании
from bot import katana_bot # Импортируем конкретный файл/модуль с логикой бота
# Это позволяет избежать запуска всего bot.py как скрипта при импорте

# Попытка импортировать nlp_processor, если он существует (для будущей интеграции)
try:
    from bot import nlp_processor # Предполагаемое имя для NLP модуля/объекта
except ImportError:
    nlp_processor = None # Если его нет, то None


class TestBot(unittest.TestCase):

    def setUp(self):
        # Create a dummy commands directory for testing
        self.test_commands_dir = Path("test_commands_temp_dir") # Using a more unique name
        self.test_commands_dir.mkdir(parents=True, exist_ok=True)

        # Store original and set to test
        self.original_command_file_dir = katana_bot.COMMAND_FILE_DIR
        katana_bot.COMMAND_FILE_DIR = self.test_commands_dir

        # Mock the bot object and its methods
        self.mock_bot_instance = MagicMock()
        # Patch the bot instance within the 'katana_bot' module
        self.bot_patcher = patch('bot.katana_bot.bot', self.mock_bot_instance) # Указываем полный путь к объекту bot
        self.mock_bot_module_instance = self.bot_patcher.start()

        # Mock datetime to control timestamps in filenames
        self.mock_datetime_patcher = patch('bot.katana_bot.datetime') # Указываем полный путь к datetime
        self.mock_datetime = self.mock_datetime_patcher.start()
        self.mock_datetime.utcnow.return_value.strftime.return_value = "YYYYMMDD_HHMMSS_ffffff"


    def tearDown(self):
        # Stop patchers
        self.bot_patcher.stop()
        self.mock_datetime_patcher.stop()

        # Clean up: remove dummy directory and its contents
        if self.test_commands_dir.exists():
            shutil.rmtree(self.test_commands_dir) # shutil.rmtree is more robust for non-empty dirs

        # Restore original
        katana_bot.COMMAND_FILE_DIR = self.original_command_file_dir


    def _create_mock_message(self, text_payload):
        mock_message = MagicMock()
        mock_message.chat.id = 12345
        mock_message.text = json.dumps(text_payload)
        return mock_message

    # --- Test Command Validation ---
    def test_valid_command_gets_saved(self):
        command = {"type": "test_type", "module": "test_module", "args": {}, "id": "test_id"}
        mock_message = self._create_mock_message(command)

        katana_bot.handle_message(mock_message) # Используем katana_bot.handle_message

        # Check file creation
        expected_module_dir = self.test_commands_dir / "telegram_mod_test_module"
        self.assertTrue(expected_module_dir.exists())

        expected_filename = f"YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
        expected_file_path = expected_module_dir / expected_filename
        self.assertTrue(expected_file_path.exists())

        with open(expected_file_path, "r") as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data, command)

        # Check reply
        self.mock_bot_module_instance.reply_to.assert_called_once()
        args, kwargs = self.mock_bot_module_instance.reply_to.call_args
        self.assertEqual(args[0], mock_message)
        self.assertTrue(args[1].startswith("✅ Command received and saved as"))
        self.assertIn(str(expected_file_path), args[1])


    def test_invalid_json_format(self):
        mock_message = MagicMock() # Simpler mock for this case
        mock_message.chat.id = 123
        mock_message.text = "not a valid json"
        katana_bot.handle_message(mock_message) # Используем katana_bot.handle_message
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "❌ Error: Invalid JSON format.")

    def test_missing_type_field(self):
        command = {"module": "test_module", "args": {}, "id": "test_id"} # type is missing
        mock_message = self._create_mock_message(command)
        katana_bot.handle_message(mock_message) # Используем katana_bot.handle_message
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "❌ Error: Missing required field 'type'.")

    def test_invalid_args_type(self):
        command = {"type": "test_type", "module": "test_module", "args": "not_a_dict", "id": "test_id"}
        mock_message = self._create_mock_message(command)
        katana_bot.handle_message(mock_message) # Используем katana_bot.handle_message
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "❌ Error: Field 'args' must be type dict. Got str.")

    def test_invalid_id_type(self):
        command = {"type": "test_type", "module": "test_module", "args": {}, "id": [1,2,3]} # id is a list
        mock_message = self._create_mock_message(command)
        katana_bot.handle_message(mock_message) # Используем katana_bot.handle_message
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "❌ Error: Field 'id' must be type str or int. Got list.")


    # --- Test Command Routing ---
    @patch('bot.katana_bot.handle_log_event') # Указываем полный путь
    def test_routing_log_event(self, mock_handle_log_event_func):
        command = {"type": "log_event", "module": "logging", "args": {"message": "hello"}, "id": "log001"}
        mock_message = self._create_mock_message(command)

        katana_bot.handle_message(mock_message) # Используем katana_bot.handle_message

        mock_handle_log_event_func.assert_called_once_with(command, mock_message.chat.id)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "✅ 'log_event' processed (placeholder).")


    @patch('bot.katana_bot.handle_mind_clearing') # Указываем полный путь
    def test_routing_mind_clearing(self, mock_handle_mind_clearing_func):
        command = {"type": "mind_clearing", "module": "wellness", "args": {"duration": "10m"}, "id": "mind002"}
        mock_message = self._create_mock_message(command)

        katana_bot.handle_message(mock_message) # Используем katana_bot.handle_message

        mock_handle_mind_clearing_func.assert_called_once_with(command, mock_message.chat.id)
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "✅ 'mind_clearing' processed (placeholder).")

    # --- Test NLP and Logging Integration (Initial Structure) ---

    @patch('bot.katana_bot.log_local_bot_event') # Mocking the logger to check calls
    @patch('bot.katana_bot.handle_nlp_command', create=True) # Мокаем гипотетический обработчик NLP команд, создаем если нет
    def test_nlp_command_integration(self, mock_handle_nlp_command, mock_log_local_bot_event):
        # Предположим, что команда с type="nlp_process" будет обрабатываться функцией handle_nlp_command
        # Эту функцию нужно будет создать в katana_bot.py
        # katana_bot.py нужно будет доработать, чтобы иметь nlp_processor (или вызывать соответствующий сервис)

        # mock_handle_nlp_command - это мок для функции, которая должна была бы обработать NLP команду.
        # На данный момент мы не будем настраивать его return_value, так как
        # основная цель этого теста - проверить, что он НЕ вызывается,
        # пока соответствующая логика маршрутизации не добавлена в katana_bot.py.
        # Позже, когда логика будет добавлена, мы будем проверять его вызов и результат.

        command_text = "Проанализируй этот текст" # Этот текст пока не используется напрямую в этом тесте
        command_payload = {
            "type": "nlp_process",
            "module": "nlp",
            "args": {"text": command_text},
            "id": "nlp001"
        }
        mock_message = self._create_mock_message(command_payload)

        # Предположим, что handle_message будет вызывать nlp_processor.process_text
        # и затем отвечать результатом. Это потребует изменений в bot.py

        # Для этого теста, мы сначала проверим, что если такой тип команды НЕ обработан специально,
        # он сохранится как обычно. Позже, когда bot.py будет обновлен, этот тест изменится.
        # Сейчас мы просто проверяем, что nlp_processor и logger вызываются (гипотетически).

        # --- Начало секции, которая будет изменена после обновления bot.py ---
        # В текущей реализации bot.py, любая неизвестная команда просто сохраняется.
        # Поэтому мы ожидаем такое поведение СЕЙЧАС.

        # Для имитации того, что NLP модуль будет вызван, и логгер тоже,
        # мы сделаем mock-вызовы внутри этого теста, как если бы katana_bot.py их делал.
        # Это не идеальный интеграционный тест, но он готовит почву.

        # Если бы katana_bot.py был обновлен для обработки 'nlp_process' и вызывал handle_nlp_command:
        # katana_bot.handle_message(mock_message)
        # mock_handle_nlp_command.assert_called_once_with(command_payload, mock_message.chat.id)
        # # Дальнейшие проверки ответа и логов, специфичных для NLP
        # --- Конец секции ---

        # ТЕКУЩЕЕ ПОВЕДЕНИЕ:
        # Поскольку katana_bot.py ЕЩЕ НЕ ИМЕЕТ специального обработчика для 'nlp_process'
        # и не вызывает гипотетический 'handle_nlp_command',
        # команда 'nlp_process' будет обработана как неизвестная команда и просто сохранена.
        # Поэтому mock_handle_nlp_command НЕ БУДЕТ вызван.
        katana_bot.handle_message(mock_message)

        # Проверяем, что команда была сохранена (текущее поведение)
        expected_module_dir = self.test_commands_dir / "telegram_mod_nlp"
        self.assertTrue(expected_module_dir.exists(), "Директория для NLP модуля должна быть создана")
        expected_filename = f"YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
        expected_file_path = expected_module_dir / expected_filename
        self.assertTrue(expected_file_path.exists(), "Файл команды NLP должен быть сохранен")

        with open(expected_file_path, "r") as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data, command_payload, "Сохраненные данные команды NLP не совпадают")

        # Проверяем, что бот ответил о сохранении
        self.mock_bot_module_instance.reply_to.assert_called_with(
            mock_message,
            f"✅ Command received and saved as `{str(expected_file_path)}`."
        )

        # Убедимся, что mock_handle_nlp_command НЕ был вызван, так как логика еще не добавлена в katana_bot.py
        mock_handle_nlp_command.assert_not_called()

        # Проверим основные логи (получение сообщения, сохранение)
        # Это дублирует часть test_logging_on_standard_command, но здесь в контексте NLP команды,
        # которая пока обрабатывается по стандартному пути.
        actual_log_calls = [call_item[0][0] for call_item in mock_log_local_bot_event.call_args_list if call_item[0]]
        self.assertIn(f"Received message from {mock_message.chat.id}: {mock_message.text}", actual_log_calls)
        self.assertIn(f"Command type 'nlp_process' not specifically handled, proceeding with default save.", actual_log_calls)
        self.assertIn(f"Saved command from {mock_message.chat.id} to {str(expected_file_path)}", actual_log_calls)


    @patch('bot.katana_bot.log_local_bot_event') # Указываем полный путь
    def test_logging_on_standard_command(self, mock_log_local_bot_event):
        command = {"type": "test_log", "module": "logging_test", "args": {}, "id": "log_test_001"}
        mock_message = self._create_mock_message(command)

        katana_bot.handle_message(mock_message) # Используем katana_bot.handle_message

        # Проверяем, что основные лог-сообщения вызываются
        # Первое сообщение - получение сообщения
        # Второе - валидация (если бы были ошибки, были бы другие сообщения)
        # Третье - о сохранении команды
        # Четвертое (возможно) - о том, что тип команды не обработан специально (если это так)

        # Точные вызовы зависят от пути выполнения в handle_message.
        # Мы ожидаем как минимум лог о получении и лог о сохранении.

        # Примерные ожидаемые вызовы (нужно будет уточнить на основе реальных логов bot.py)
        expected_calls = [
            call(f"Received message from {mock_message.chat.id}: {mock_message.text}"),
            call(f"Command type 'test_log' not specifically handled, proceeding with default save."),
            call(f"Saved command from {mock_message.chat.id} to {self.test_commands_dir / 'telegram_mod_logging_test' / f'YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json'}")
        ]

        # Проверяем, что эти вызовы были среди всех вызовов к логгеру
        # Используем list(mock_log_local_bot_event.mock_calls) для отладки если нужно
        # print(list(mock_log_local_bot_event.mock_calls))

        # Проверим, что определенные вызовы были сделаны. Порядок может иметь значение.
        # В данном случае, мы знаем, что `log_local_bot_event` вызывается несколько раз.
        # Мы проверим, что ожидаемые вызовы присутствуют.

        # Чтобы сделать проверку более надежной, можно проверить наличие подстрок в вызовах,
        # если точные сообщения могут немного меняться.

        # На данный момент, проверим, что бот ответил о сохранении (это косвенно говорит о пути выполнения)
        expected_module_dir = self.test_commands_dir / "telegram_mod_logging_test"
        expected_filename = f"YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
        expected_file_path = expected_module_dir / expected_filename
        self.assertTrue(expected_file_path.exists()) # Убедимся, что файл сохранен

        self.mock_bot_module_instance.reply_to.assert_called_once()
        args, kwargs = self.mock_bot_module_instance.reply_to.call_args
        self.assertTrue(args[1].startswith("✅ Command received and saved as"))

        # Проверка вызовов логгера:
        # Мы должны увидеть лог о получении сообщения и лог о сохранении.
        # Также лог о том, что команда не обработана специфично.

        # Отладочный вывод
        # print("mock_log_local_bot_event.call_args_list:", mock_log_local_bot_event.call_args_list)
        # print("mock_log_local_bot_event.mock_calls:", mock_log_local_bot_event.mock_calls)

        # Получаем все фактические вызовы к моку
        actual_log_calls = [call_item[0][0] for call_item in mock_log_local_bot_event.call_args_list if call_item[0]]

        self.assertIn(f"Received message from {mock_message.chat.id}: {mock_message.text}", actual_log_calls)
        self.assertIn(f"Command type 'test_log' not specifically handled, proceeding with default save.", actual_log_calls)
        self.assertIn(f"Saved command from {mock_message.chat.id} to {str(expected_file_path)}", actual_log_calls)


    def test_unknown_command_type_saves_normally(self):
        command = {"type": "unknown_type", "module": "custom_module", "args": {}, "id": "custom003"}
        mock_message = self._create_mock_message(command)

        katana_bot.handle_message(mock_message) # Используем katana_bot.handle_message

        # Check file creation
        expected_module_dir = self.test_commands_dir / "telegram_mod_custom_module"
        self.assertTrue(expected_module_dir.exists())

        expected_filename = f"YYYYMMDD_HHMMSS_ffffff_{mock_message.chat.id}.json"
        expected_file_path = expected_module_dir / expected_filename
        self.assertTrue(expected_file_path.exists())

        with open(expected_file_path, "r") as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data, command)

        # Check reply
        self.mock_bot_module_instance.reply_to.assert_called_once()
        args, kwargs = self.mock_bot_module_instance.reply_to.call_args
        self.assertEqual(args[0], mock_message)
        self.assertTrue(args[1].startswith("✅ Command received and saved as"))
        self.assertIn(str(expected_file_path), args[1])


if __name__ == '__main__':
    unittest.main()
