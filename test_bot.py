import unittest
from unittest.mock import MagicMock, patch, call
import json
from pathlib import Path
import shutil # For robust directory removal
import os # For main execution context
import time
import requests

import bot
from katana_state import KatanaState
import importlib

class TestBot(unittest.TestCase):
    def setUp(self):
        self.patcher = patch('bot.telebot.TeleBot')
        self.mock_bot_class = self.patcher.start()
        self.mock_bot = self.mock_bot_class.return_value

    def tearDown(self):
        self.patcher.stop()

    def _create_mock_message(self, text_payload_dict_or_str):
        mock_message = MagicMock()
        mock_message.chat.id = 12345
        if isinstance(text_payload_dict_or_str, dict):
            mock_message.text = json.dumps(text_payload_dict_or_str)
        else: # It's a string (for invalid JSON test)
            mock_message.text = text_payload_dict_or_str
        return mock_message

    def test_start_handler_registered(self):
        bot.create_bot("dummy_token", bot_class=self.mock_bot_class)
        self.mock_bot.message_handler.assert_called()

    def test_handle_message_logic_valid_command(self):
        mock_bot = MagicMock()
        command = {"type": "test_type", "module": "test_module", "args": {"data": "value"}, "id": "test_id_valid"}
        mock_message = self._create_mock_message(command)

        with patch('bot.katana_state.enqueue') as mock_enqueue:
            mock_enqueue.return_value = "test_uid"
            bot.handle_message_logic(mock_bot, mock_message)

            mock_enqueue.assert_called_once()
            args, _ = mock_enqueue.call_args
            enqueued_command = args[0]
            self.assertEqual(enqueued_command['type'], command['type'])
            self.assertEqual(enqueued_command['module'], command['module'])
            self.assertEqual(enqueued_command['args'], command['args'])
            self.assertEqual(enqueued_command['id'], command['id'])
            self.assertEqual(enqueued_command['chat_id'], mock_message.chat.id)

            mock_bot.reply_to.assert_called_with(
                mock_message,
                "✅ Command received and queued with ID: test_uid"
            )

    def test_handle_message_logic_invalid_json(self):
        mock_bot = MagicMock()
        invalid_json_string = "not a valid json"
        mock_message = self._create_mock_message(invalid_json_string)
        bot.handle_message_logic(mock_bot, mock_message)
        mock_bot.reply_to.assert_called_with(mock_message, "Error: Invalid JSON format.")

class TestCommandProcessor(unittest.TestCase):
    @patch('bot.katana_state')
    @patch('bot.handle_log_event')
    def test_log_event_command_is_processed(self, mock_handle_log_event, mock_katana_state):
        command = {"type": "log_event", "module": "test", "args": {}, "id": 1, "chat_id": 123}
        side_effect_list = [command, None]
        mock_katana_state.dequeue.side_effect = lambda: side_effect_list.pop(0)

        with patch('time.sleep'):
            bot.command_processor_loop()

        mock_handle_log_event.assert_called_once_with(command, 123)
        mock_katana_state.task_done.assert_called_once()

    @patch('bot.katana_state')
    @patch('bot.handle_n8n_trigger')
    def test_n8n_trigger_command_is_processed(self, mock_handle_n8n_trigger, mock_katana_state):
        command = {"type": "n8n_trigger", "module": "test", "args": {}, "id": 1, "chat_id": 123}
        side_effect_list = [command, None]
        mock_katana_state.dequeue.side_effect = lambda: side_effect_list.pop(0)

        with patch('time.sleep'):
            bot.command_processor_loop()

        mock_handle_n8n_trigger.assert_called_once_with(command, 123)
        mock_katana_state.task_done.assert_called_once()

    @patch('requests.post')
    def test_handle_n8n_trigger_success(self, mock_post):
        with patch('bot.katana_logger'):
            command = {"type": "n8n_trigger", "katana_uid": "test_uid"}
            mock_post.return_value.status_code = 200
            mock_post.return_value.text = "Success"

            bot.handle_n8n_trigger(command, 123)

            mock_post.assert_called_once()

    @patch('requests.post')
    def test_handle_n8n_trigger_retry_and_fail(self, mock_post):
        with patch('bot.katana_logger'):
            command = {"type": "n8n_trigger", "katana_uid": "test_uid"}
            mock_post.side_effect = requests.exceptions.RequestException("Test error")

            with patch('time.sleep'):
                bot.handle_n8n_trigger(command, 123)

            self.assertEqual(mock_post.call_count, 3)
