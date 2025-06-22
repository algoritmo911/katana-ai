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

    @patch('bot.katana_bot.logging.info')
    @patch('bot.katana_bot.logging.warning')
    @patch('bot.katana_bot.logging.error')
    @patch('bot.katana_bot.handle_nlp_command', create=True) # Мокаем гипотетический обработчик NLP команд, создаем если нет
    def test_nlp_command_integration(self, mock_handle_nlp_command, mock_log_error, mock_log_warning, mock_log_info):
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

        # Check for the detailed message log first
        # Example: logging.info(f"Received message update from chat_id {chat_id}. Full message object: {message_dict}")
        # We'll check for a substring as the full dict can be complex.
        self.assertTrue(any(f"Received message update from chat_id {mock_message.chat.id}" in call_args[0][0] for call_args in mock_log_info.call_args_list))
        mock_log_info.assert_any_call(f"Successfully parsed JSON for chat_id {mock_message.chat.id}: {command_payload}")
        mock_log_info.assert_any_call(f"Command type 'nlp_process' not specifically handled, proceeding with default save.")
        mock_log_info.assert_any_call(f"Saved command from {mock_message.chat.id} to {str(expected_file_path)}")


    @patch('bot.katana_bot.logging.info')
    @patch('bot.katana_bot.logging.warning') # Added for completeness, though not expected in this specific test
    @patch('bot.katana_bot.logging.error')   # Added for completeness
    def test_logging_on_standard_command(self, mock_log_error, mock_log_warning, mock_log_info):
        command = {"type": "test_log", "module": "logging_test", "args": {}, "id": "log_test_001"}
        mock_message = self._create_mock_message(command)

        katana_bot.handle_message(mock_message)

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

        # Check for the detailed message log first
        self.assertTrue(any(f"Received message update from chat_id {mock_message.chat.id}" in call_args[0][0] for call_args in mock_log_info.call_args_list))
        mock_log_info.assert_any_call(f"Successfully parsed JSON for chat_id {mock_message.chat.id}: {command}")
        mock_log_info.assert_any_call(f"Command type 'test_log' not specifically handled, proceeding with default save.")
        mock_log_info.assert_any_call(f"Saved command from {mock_message.chat.id} to {str(expected_file_path)}")

        # Ensure no error or warning logs were made for this successful case
        mock_log_error.assert_not_called()
        mock_log_warning.assert_not_called()


    @patch('bot.katana_bot.logging.info') # For logging successful save
    def test_unknown_command_type_saves_normally(self, mock_log_info):
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
        self.assertTrue(args[1].startswith("✅ Команда получена и сохранена как")) # Check for Russian message
        self.assertIn(str(expected_file_path), args[1])

        # Verify logging calls
        self.assertTrue(any(f"Received message update from chat_id {mock_message.chat.id}" in call_args[0][0] for call_args in mock_log_info.call_args_list))
        mock_log_info.assert_any_call(f"Successfully parsed JSON for chat_id {mock_message.chat.id}: {command}")
        mock_log_info.assert_any_call(f"Command type 'unknown_type' not specifically handled, proceeding with default save.")
        mock_log_info.assert_any_call(f"Saved command from {mock_message.chat.id} to {str(expected_file_path)}")


    # --- Test Error Handling and User Feedback ---
    @patch('bot.katana_bot.logging.error')
    def test_invalid_json_format_reply_and_log(self, mock_log_error):
        mock_message = MagicMock()
        mock_message.chat.id = 123
        mock_message.text = "not a valid json"

        katana_bot.handle_message(mock_message)

        # Check user reply
        self.mock_bot_module_instance.reply_to.assert_called_once()
        args, _ = self.mock_bot_module_instance.reply_to.call_args
        self.assertEqual(args[0], mock_message)
        self.assertIn("❌ Ошибка: Некорректный формат JSON.", args[1])
        self.assertIn("Детали:", args[1]) # Check that details are mentioned

        # Check error log
        mock_log_error.assert_called_once()
        log_args, _ = mock_log_error.call_args
        self.assertIn(f"Invalid JSON from chat_id {mock_message.chat.id}. Text: '{mock_message.text}'. Error:", log_args[0])

    @patch('bot.katana_bot.logging.error')
    def test_missing_required_field_reply_and_log(self, mock_log_error):
        command = {"module": "test_module", "args": {}, "id": "test_id"} # type is missing
        mock_message = self._create_mock_message(command)

        katana_bot.handle_message(mock_message)

        self.mock_bot_module_instance.reply_to.assert_called_once()
        args, _ = self.mock_bot_module_instance.reply_to.call_args
        self.assertEqual(args[0], mock_message)
        self.assertIn("❌ Ошибка валидации команды:", args[1])
        self.assertIn("Отсутствует обязательное поле 'type'.", args[1])

        mock_log_error.assert_called_once()
        log_args, _ = mock_log_error.call_args
        self.assertIn(f"Command validation failed for chat_id {mock_message.chat.id}", log_args[0])
        self.assertIn("Отсутствует обязательное поле 'type'.", log_args[0])
        self.assertIn(f"Command: {mock_message.text}", log_args[0])

    @patch('bot.katana_bot.logging.error')
    def test_invalid_field_type_reply_and_log(self, mock_log_error):
        command = {"type": "test_type", "module": "test_module", "args": "not_a_dict", "id": "test_id"}
        mock_message = self._create_mock_message(command)

        katana_bot.handle_message(mock_message)

        self.mock_bot_module_instance.reply_to.assert_called_once()
        args, _ = self.mock_bot_module_instance.reply_to.call_args
        self.assertEqual(args[0], mock_message)
        self.assertIn("❌ Ошибка валидации команды:", args[1])
        self.assertIn("Поле 'args' должно быть типа dict. Получено: str.", args[1])

        mock_log_error.assert_called_once()
        log_args, _ = mock_log_error.call_args
        self.assertIn(f"Command validation failed for chat_id {mock_message.chat.id}", log_args[0])
        self.assertIn("Поле 'args' должно быть типа dict. Получено: str.", log_args[0])

    @patch('bot.katana_bot.logging.error')
    @patch('bot.katana_bot.logging.info') # To check it's not saved
    @patch('builtins.open', new_callable=unittest.mock.mock_open) # Mock open to simulate IOError
    def test_save_command_io_error(self, mock_open_file, mock_log_info, mock_log_error):
        command = {"type": "io_error_test", "module": "test_module", "args": {}, "id": "io_test_id"}
        mock_message = self._create_mock_message(command)

        # Simulate IOError on file write
        mock_open_file.side_effect = IOError("Disk full")

        katana_bot.handle_message(mock_message)

        # Check user reply
        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "❌ Ошибка: Не удалось сохранить команду на сервере.")

        # Check error log
        mock_log_error.assert_called_once()
        log_args, _ = mock_log_error.call_args
        self.assertIn(f"Failed to save command from {mock_message.chat.id}", log_args[0])
        self.assertIn("Error: Disk full", log_args[0])

        # Ensure the "Saved command..." log was NOT called
        for call_args in mock_log_info.call_args_list:
            self.assertNotIn("Saved command from", call_args[0][0])


    # Test for the /start command logging
    @patch('bot.katana_bot.logging.info')
    def test_handle_start_logging(self, mock_log_info):
        mock_message = MagicMock()
        mock_message.chat.id = 78901

        katana_bot.handle_start(mock_message)

        self.mock_bot_module_instance.reply_to.assert_called_with(mock_message, "Привет! Я — Katana. Отправь JSON-команду, чтобы начать.")
        mock_log_info.assert_called_with(f"/start received from {mock_message.chat.id}")


if __name__ == '__main__':
    unittest.main()
