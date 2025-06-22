# tests/test_nlp_module.py
import unittest
from nlp_module import recognize_intent

class TestNLPModule(unittest.TestCase):

    def test_recognize_uptime_intent(self):
        test_cases = [
            "What is the system uptime?",
            "tell me the uptime",
            "uptime please",
            "SYSTEM UPTIME"
        ]
        for msg in test_cases:
            with self.subTest(msg=msg):
                intent, params = recognize_intent(msg)
                self.assertEqual(intent, "get_uptime")
                self.assertEqual(params, {})

    def test_recognize_run_command_intent(self):
        test_cases = [
            ("/run get_status --verbose", "get_status --verbose"),
            ("/run uptime", "uptime"),
            ("/run ps aux | grep python", "ps aux | grep python"),
            ("/RUN list_users", "list_users") # Test case-insensitivity of /run
        ]
        for msg, expected_cmd in test_cases:
            with self.subTest(msg=msg):
                intent, params = recognize_intent(msg)
                self.assertEqual(intent, "run_command")
                self.assertEqual(params, {"command": expected_cmd})

    def test_run_command_with_no_actual_command_or_spaces(self):
        # The regex `.+` requires at least one character after /run and space
        intent, params = recognize_intent("/run")
        self.assertIsNone(intent, "Should not recognize '/run' without command as run_command intent")

        intent, params = recognize_intent("/run ")
        self.assertIsNone(intent, "Should not recognize '/run ' (with space but no command) as run_command intent")

        intent, params = recognize_intent("/run      ") # With trailing spaces
        self.assertIsNone(intent, "Should not recognize '/run      ' (with spaces but no command) as run_command intent")


    def test_recognize_greet_intent(self):
        test_cases = [
            ("Hello bot", None),
            ("Hi there", None),
            ("Greet me", None),
            ("hi", None),
            ("greet", None),
            ("Greet John", "John"),
            ("Hello to Jane Doe", "Jane Doe"),
            ("hi to Michael", "Michael"),
            ("greet   Mary Ann  ", "Mary Ann"),
            ("Hello    My Friend", "My Friend")
        ]
        for msg, expected_name in test_cases:
            with self.subTest(msg=msg):
                intent, params = recognize_intent(msg)
                self.assertEqual(intent, "greet_user")
                if expected_name:
                    self.assertEqual(params, {"name": expected_name})
                else:
                    self.assertEqual(params, {})

    def test_no_intent_recognized(self):
        test_cases = [
            "What is the weather today?",
            "Tell me a joke.",
            "Book a flight to London",
            "How are you?"
        ]
        for msg in test_cases:
            with self.subTest(msg=msg):
                intent, params = recognize_intent(msg)
                self.assertIsNone(intent)
                self.assertEqual(params, {})

    def test_empty_or_none_message(self):
        intent, params = recognize_intent("")
        self.assertIsNone(intent)
        self.assertEqual(params, {})

        intent, params = recognize_intent(None)
        self.assertIsNone(intent)
        self.assertEqual(params, {})

    def test_mixed_case_intents(self):
        intent, params = recognize_intent("Tell me the UpTiMe")
        self.assertEqual(intent, "get_uptime")
        self.assertEqual(params, {})

        intent, params = recognize_intent("GrEeT sAm")
        self.assertEqual(intent, "greet_user")
        self.assertEqual(params, {"name": "Sam"})


if __name__ == '__main__':
    unittest.main()
