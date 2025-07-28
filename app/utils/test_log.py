import unittest
import os
import json
from app.utils.log import log_command, COMMAND_LOG_FILE

class TestLog(unittest.TestCase):
    def tearDown(self):
        if os.path.exists(COMMAND_LOG_FILE):
            os.remove(COMMAND_LOG_FILE)

    def test_log_command(self):
        log_command(
            command_id="test_id",
            command="test_command",
            args={"test": "arg"},
            status="success",
            result={"test": "result"},
        )
        self.assertTrue(os.path.exists(COMMAND_LOG_FILE))
        with open(COMMAND_LOG_FILE, "r") as f:
            log_entry = json.loads(f.read())
            self.assertEqual(log_entry["command_id"], "test_id")
            self.assertEqual(log_entry["command"], "test_command")
            self.assertEqual(log_entry["args"], {"test": "arg"})
            self.assertEqual(log_entry["status"], "success")
            self.assertEqual(log_entry["result"], {"test": "result"})

if __name__ == '__main__':
    unittest.main()
