import unittest
from unittest.mock import MagicMock, patch, call
import json
import os
import redis # For redis.exceptions
from datetime import datetime, timezone

# Ensure src is discoverable for imports, assuming tests are run from project root
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.memory.memory_manager import MemoryManager

class TestMemoryManager(unittest.TestCase):

    def setUp(self):
        self.mock_redis_client = MagicMock(spec=redis.Redis)

        self.patcher = patch('redis.Redis', return_value=self.mock_redis_client)
        self.mock_redis_class = self.patcher.start()

        self.redis_host = 'testhost'
        self.redis_port = 1234
        self.redis_db = 0
        self.redis_password = 'testpassword'
        self.default_ttl = MemoryManager.DEFAULT_TTL_SECONDS

        self.manager = MemoryManager(
            host=self.redis_host,
            port=self.redis_port,
            db=self.redis_db,
            password=self.redis_password,
            chat_history_ttl_seconds=self.default_ttl
        )
        self.mock_redis_class.assert_called_once_with(
            host=self.redis_host, port=self.redis_port, db=self.redis_db, password=self.redis_password, decode_responses=False
        )
        self.mock_redis_client.ping.assert_called_once()
        self.mock_redis_client.reset_mock()


    def tearDown(self):
        self.patcher.stop()

    def test_initialization_connection_error(self):
        self.patcher.stop() # Stop main patcher

        mock_redis_instance_for_error = MagicMock(spec=redis.Redis)
        mock_redis_instance_for_error.ping.side_effect = redis.exceptions.ConnectionError("Test connection error")

        with patch('redis.Redis', return_value=mock_redis_instance_for_error) as mock_class_for_error:
            # Patch the module-level logger directly
            with patch('src.memory.memory_manager.logger.error') as mock_log_error:
                manager_conn_error = MemoryManager(host='badhost', port=666)
                self.assertIsNone(manager_conn_error.redis_client)
                mock_log_error.assert_called_once()
                self.assertIn("Failed to connect to Redis at badhost:666/0", mock_log_error.call_args[0][0])

        self.patcher.start() # Restart main patcher for other tests
        self.mock_redis_client.reset_mock()


    def test_get_chat_key(self):
        self.assertEqual(self.manager._get_chat_key("123"), "chat_history:123")

    def test_add_message_to_history(self):
        chat_id = "chat1"
        message = {"role": "user", "content": "Hello"}

        self.mock_redis_client.llen.return_value = 1
        self.manager.add_message_to_history(chat_id, message)

        args, _ = self.mock_redis_client.rpush.call_args
        self.assertEqual(args[0], f"chat_history:{chat_id}")
        pushed_message = json.loads(args[1].decode('utf-8') if isinstance(args[1], bytes) else args[1])

        self.assertEqual(pushed_message["role"], "user")
        self.assertEqual(pushed_message["content"], "Hello")
        self.assertTrue("timestamp" in pushed_message)
        self.mock_redis_client.expire.assert_called_once_with(f"chat_history:{chat_id}", self.default_ttl)

    def test_add_message_with_existing_timestamp(self):
        chat_id = "chat_ts"
        fixed_timestamp = datetime.now(timezone.utc).isoformat()
        message = {"role": "assistant", "content": "Reply", "timestamp": fixed_timestamp}

        self.manager.add_message_to_history(chat_id, message)

        args, _ = self.mock_redis_client.rpush.call_args
        pushed_message = json.loads(args[1].decode('utf-8') if isinstance(args[1], bytes) else args[1])
        self.assertEqual(pushed_message["timestamp"], fixed_timestamp)

    def test_add_message_missing_role_or_content(self):
        chat_id = "chat_invalid"
        message_no_role = {"content": "No role"}
        message_no_content = {"role": "user"}

        with patch('src.memory.memory_manager.logger.error') as mock_log_error:
            self.manager.add_message_to_history(chat_id, message_no_role)
            self.assertTrue(mock_log_error.called)
            args, _ = mock_log_error.call_args
            self.assertIn(f"Message for chat {chat_id} is missing 'role' or 'content'.", args[0])
            self.assertIn("'content': 'No role'", args[0])
            self.mock_redis_client.rpush.assert_not_called()

            mock_log_error.reset_mock()
            self.mock_redis_client.rpush.reset_mock() # Also reset rpush mock for clean assert
            self.manager.add_message_to_history(chat_id, message_no_content)
            self.assertTrue(mock_log_error.called)
            args, _ = mock_log_error.call_args
            self.assertIn(f"Message for chat {chat_id} is missing 'role' or 'content'.", args[0])
            self.assertIn("'role': 'user'", args[0])
            self.mock_redis_client.rpush.assert_not_called()

    def test_get_history_empty(self):
        chat_id = "empty_chat"
        self.mock_redis_client.lrange.return_value = []
        history = self.manager.get_history(chat_id)
        self.assertEqual(history, [])
        self.mock_redis_client.lrange.assert_called_once_with(f"chat_history:{chat_id}", 0, -1)
        self.mock_redis_client.expire.assert_not_called()

    def test_get_history_with_messages(self):
        chat_id = "chat_with_msgs"
        msg1 = {"role": "user", "content": "Hi", "timestamp": datetime.now(timezone.utc).isoformat()}
        msg2 = {"role": "assistant", "content": "Hello", "timestamp": datetime.now(timezone.utc).isoformat()}

        self.mock_redis_client.lrange.return_value = [ json.dumps(msg1).encode('utf-8'), json.dumps(msg2).encode('utf-8') ]
        history = self.manager.get_history(chat_id)

        self.assertEqual(len(history), 2)
        self.assertEqual(history[0], msg1)
        self.assertEqual(history[1], msg2)
        self.mock_redis_client.lrange.assert_called_once_with(f"chat_history:{chat_id}", 0, -1)
        self.mock_redis_client.expire.assert_called_once_with(f"chat_history:{chat_id}", self.default_ttl)

    def test_get_history_with_limit(self):
        chat_id = "chat_limit"
        msg_limit = {"role":"user", "content":"msg_limited"}
        self.mock_redis_client.lrange.return_value = [json.dumps(msg_limit).encode('utf-8')]
        self.manager.get_history(chat_id, limit=1)
        self.mock_redis_client.lrange.assert_called_once_with(f"chat_history:{chat_id}", -1, -1)
        self.mock_redis_client.expire.assert_called_once()

    def test_get_history_json_decode_error(self):
        chat_id = "chat_decode_error"
        valid_msg_dict = {"role": "user", "content": "Valid"}
        valid_msg_json_bytes = json.dumps(valid_msg_dict).encode('utf-8')
        invalid_json_bytes = b"this is not json"

        self.mock_redis_client.lrange.return_value = [invalid_json_bytes, valid_msg_json_bytes]
        with patch('src.memory.memory_manager.logger.warning') as mock_log_warning:
            history = self.manager.get_history(chat_id)
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0], valid_msg_dict)
            mock_log_warning.assert_called_once()
            self.assertIn(f"Failed to decode JSON for a message in chat {chat_id}", mock_log_warning.call_args[0][0])

    def test_clear_history(self):
        chat_id = "chat_to_clear"
        self.mock_redis_client.delete.return_value = 1
        self.manager.clear_history(chat_id)
        self.mock_redis_client.delete.assert_called_once_with(f"chat_history:{chat_id}")

    def test_clear_history_not_found(self):
        chat_id = "chat_not_existing_to_clear"
        self.mock_redis_client.delete.return_value = 0
        self.manager.clear_history(chat_id)
        self.mock_redis_client.delete.assert_called_once_with(f"chat_history:{chat_id}")

    def test_redis_error_on_add(self):
        self.mock_redis_client.rpush.side_effect = redis.exceptions.RedisError("Test RPUSH Error")
        with patch('src.memory.memory_manager.logger.error') as mock_log_error:
            self.manager.add_message_to_history("err_chat_add", {"role": "user", "content": "test"})
            mock_log_error.assert_called_once()
            self.assertIn("Redis error while adding message", mock_log_error.call_args[0][0])

    def test_redis_error_on_get(self):
        self.mock_redis_client.lrange.side_effect = redis.exceptions.RedisError("Test LRANGE Error")
        with patch('src.memory.memory_manager.logger.error') as mock_log_error:
            history = self.manager.get_history("err_chat_get")
            self.assertEqual(history, [])
            mock_log_error.assert_called_once()
            self.assertIn("Redis error while getting history", mock_log_error.call_args[0][0])

    def test_redis_error_on_clear(self):
        self.mock_redis_client.delete.side_effect = redis.exceptions.RedisError("Test DELETE Error")
        with patch('src.memory.memory_manager.logger.error') as mock_log_error:
            self.manager.clear_history("err_chat_clear")
            mock_log_error.assert_called_once()
            self.assertIn("Redis error while clearing history", mock_log_error.call_args[0][0])

    def test_ttl_disabled(self):
        self.patcher.stop() # Stop main patcher

        mock_redis_client_no_ttl = MagicMock(spec=redis.Redis)
        mock_redis_client_no_ttl.ping.return_value = True # Simulate successful ping

        with patch('redis.Redis', return_value=mock_redis_client_no_ttl):
            manager_no_ttl = MemoryManager(chat_history_ttl_seconds=0) # Disable TTL
            self.assertIsNone(manager_no_ttl.ttl_seconds)

            manager_no_ttl.add_message_to_history("chat_no_ttl", {"role":"user", "content":"test"})
            mock_redis_client_no_ttl.rpush.assert_called_once()
            mock_redis_client_no_ttl.expire.assert_not_called()

            mock_redis_client_no_ttl.lrange.return_value = [json.dumps({"role":"user", "content":"test"}).encode('utf-8')]
            manager_no_ttl.get_history("chat_no_ttl")
            mock_redis_client_no_ttl.lrange.assert_called_once()
            mock_redis_client_no_ttl.expire.assert_not_called()

        self.patcher.start() # Restart main patcher
        self.mock_redis_client.reset_mock()

if __name__ == '__main__':
    unittest.main()
