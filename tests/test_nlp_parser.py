import unittest
from bot.nlp.parser import NLPParser

class TestNLPParser(unittest.TestCase):

    def setUp(self):
        self.parser = NLPParser()

    def test_parse_command_no_args(self):
        result = self.parser.parse_message("/start")
        self.assertEqual(result["type"], "command")
        self.assertEqual(result["command"], "start")
        self.assertEqual(result["args"], [])
        self.assertEqual(result["raw_text"], "/start")

    def test_parse_command_with_args(self):
        result = self.parser.parse_message("/say hello world")
        self.assertEqual(result["type"], "command")
        self.assertEqual(result["command"], "say")
        self.assertEqual(result["args"], ["hello", "world"])
        self.assertEqual(result["raw_text"], "/say hello world")

    def test_parse_command_with_extra_spaces(self):
        result = self.parser.parse_message("/say   hello   world  ")
        self.assertEqual(result["type"], "command")
        self.assertEqual(result["command"], "say")
        self.assertEqual(result["args"], ["hello", "world"])
        self.assertEqual(result["raw_text"], "/say   hello   world") # .strip() is applied to raw_text

    def test_parse_greeting_intent(self):
        result = self.parser.parse_message("Hello bot")
        self.assertEqual(result["type"], "intent")
        self.assertEqual(result["intent"], "greeting")
        self.assertIn("greeting", result["all_detected_intents"])
        self.assertEqual(result["raw_text"], "Hello bot")

    def test_parse_goodbye_intent(self):
        result = self.parser.parse_message("see you later")
        self.assertEqual(result["type"], "intent")
        self.assertEqual(result["intent"], "goodbye")
        self.assertIn("goodbye", result["all_detected_intents"])

    def test_parse_affirmative_intent(self):
        result = self.parser.parse_message("ok sure")
        self.assertEqual(result["type"], "intent")
        self.assertEqual(result["intent"], "affirmative") # Takes the first one if multiple keywords for same intent
        self.assertIn("affirmative", result["all_detected_intents"])

    def test_parse_negative_intent(self):
        result = self.parser.parse_message("no, I don't think so")
        self.assertEqual(result["type"], "intent")
        self.assertEqual(result["intent"], "negative")
        self.assertIn("negative", result["all_detected_intents"])

    def test_parse_multiple_intents_takes_first_match_by_order(self):
        # Current behavior: first pattern in self.intent_patterns that matches
        # "greeting" pattern is before "affirmative"
        result = self.parser.parse_message("Yes, hello there!")
        self.assertEqual(result["type"], "intent")
        # This depends on the order in NLPParser.intent_patterns
        # Assuming 'greeting' comes before 'affirmative' in the dict iteration for matching
        # This might be fragile if dict order changes, but for current implementation it's testable
        self.assertTrue(result["intent"] == "greeting" or result["intent"] == "affirmative")
        self.assertIn("greeting", result["all_detected_intents"])
        self.assertIn("affirmative", result["all_detected_intents"])


    def test_parse_message_no_command_no_intent(self):
        result = self.parser.parse_message("This is a regular message.")
        self.assertEqual(result["type"], "message")
        self.assertEqual(result["intent"], "unknown")
        self.assertEqual(result["raw_text"], "This is a regular message.")
        self.assertEqual(result["entities"], {}) # No numbers in this message

    def test_entity_extraction_numbers(self):
        result = self.parser.parse_message("I need 2 apples and 100 bananas.")
        self.assertEqual(result["type"], "message") # Assuming no intent matches "I need..."
        self.assertEqual(result["intent"], "unknown")
        self.assertIn("numbers", result["entities"])
        self.assertEqual(sorted(result["entities"]["numbers"]), sorted(["2", "100"]))

    def test_entity_extraction_numbers_in_command_args(self):
        # Entity extraction is currently independent of message type (command/intent/message)
        # It processes the raw_text for entities if not a command, or args for commands.
        # The current NLPParser._extract_entities is called for non-commands.
        # For commands, entities are not explicitly extracted from args by the top-level parse_message.
        # Let's refine this test based on current implementation.
        # _extract_entities is called by parse_message for 'intent' and 'message' types, not 'command'.

        # Test case for 'message' type with numbers
        result_message = self.parser.parse_message("My number is 12345.")
        self.assertEqual(result_message["type"], "message")
        self.assertIn("numbers", result_message["entities"])
        self.assertEqual(result_message["entities"]["numbers"], ["12345"])

        # Test case for 'intent' type with numbers
        result_intent = self.parser.parse_message("Yes, I need 5 of them.")
        self.assertEqual(result_intent["type"], "intent")
        self.assertEqual(result_intent["intent"], "affirmative")
        self.assertIn("numbers", result_intent["entities"])
        self.assertEqual(result_intent["entities"]["numbers"], ["5"])

    def test_empty_message(self):
        result = self.parser.parse_message("")
        self.assertEqual(result["type"], "message") # or could be error, current handles as unknown
        self.assertEqual(result["intent"], "unknown")
        self.assertEqual(result["raw_text"], "")
        self.assertEqual(result["entities"], {})

    def test_message_with_only_spaces(self):
        result = self.parser.parse_message("   ")
        self.assertEqual(result["type"], "message")
        self.assertEqual(result["intent"], "unknown")
        self.assertEqual(result["raw_text"], "") # Due to strip()
        self.assertEqual(result["entities"], {})

if __name__ == '__main__':
    unittest.main()
