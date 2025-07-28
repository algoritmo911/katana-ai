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

    def test_command_priority(self):
        # Enqueue two commands with different priorities
        low_priority_command = {"type": "test_type", "priority": 200}
        high_priority_command = {"type": "test_type", "priority": 10}

        # We need to manually call enqueue to control the order
        state = KatanaState()
        state.enqueue(low_priority_command)
        state.enqueue(high_priority_command)

        # Dequeue commands and check their order
        dequeued_high = state.dequeue()
        dequeued_low = state.dequeue()

        self.assertEqual(dequeued_high.get('priority'), 10)
        self.assertEqual(dequeued_low.get('priority'), 200)

    @patch('bot.handle_log_event')
    def test_command_cancellation(self, mock_handle_log_event):
        state = KatanaState()
        command_to_cancel = {"type": "log_event", "id": "cancel_this"}
        command_to_process = {"type": "log_event", "id": "process_this"}

        # Enqueue both
        uid_to_cancel = state.enqueue(command_to_cancel)
        state.enqueue(command_to_process)

        # Cancel one
        state.cancel_command(uid_to_cancel)

        # Process the queue
        with patch('bot.katana_state', state):
            with patch('time.sleep'):
                 # Since the loop breaks on None, we need to add it to the queue
                state.enqueue({"type": "poison_pill"})
                # This is a hacky way to stop the loop for the test
                original_dequeue = state.dequeue
                def dequeue_with_stop():
                    item = original_dequeue()
                    if item and item.get("type") == "poison_pill":
                        return None
                    return item
                state.dequeue = dequeue_with_stop
                bot.command_processor_loop()

        # Assert that only the non-cancelled command was processed
        mock_handle_log_event.assert_called_once()
        self.assertEqual(mock_handle_log_event.call_args[0][0]['id'], "process_this")

    @patch('bot.handle_log_event')
    def test_overwrite_result(self, mock_handle_log_event):
        state = KatanaState()
        command = {"type": "log_event", "id": "overwrite_this", "overwrite_result": True}

        # Enqueue the same command twice
        state.enqueue(command)
        state.enqueue(command)

        # Process the queue
        with patch('bot.katana_state', state):
            with patch('time.sleep'):
                # Add poison pill to stop the loop
                state.enqueue({"type": "poison_pill"})
                original_dequeue = state.dequeue
                def dequeue_with_stop():
                    item = original_dequeue()
                    if item and item.get("type") == "poison_pill":
                        return None
                    return item
                state.dequeue = dequeue_with_stop
                bot.command_processor_loop()

        # Assert that the command was processed twice
        self.assertEqual(mock_handle_log_event.call_count, 2)


    @patch('requests.post')
    def test_callback_url_is_called(self, mock_post):
        with patch('bot.katana_logger'):
            command = {
                "type": "test_type",
                "katana_uid": "test_uid",
                "callback_url": "http://localhost:1234/callback"
            }
            side_effect_list = [command, None]
            with patch('bot.katana_state') as mock_katana_state:
                mock_katana_state.dequeue.side_effect = lambda: side_effect_list.pop(0)
                with patch('time.sleep'):
                    bot.command_processor_loop()

            mock_post.assert_called_with("http://localhost:1234/callback", json=command)
