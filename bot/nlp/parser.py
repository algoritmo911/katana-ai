import re

class NLPParser:
    def __init__(self):
        # Basic command pattern: starts with '/' followed by a word
        self.command_pattern = re.compile(r"^\/(\w+)\s*(.*)")
        # Simple keyword patterns (examples, can be expanded)
        self.intent_patterns = {
            "greeting": re.compile(r"\b(hello|hi|hey|greetings)\b", re.IGNORECASE),
            "goodbye": re.compile(r"\b(bye|goodbye|see you)\b", re.IGNORECASE),
            "affirmative": re.compile(r"\b(yes|yeah|ok|sure)\b", re.IGNORECASE),
            "negative": re.compile(r"\b(no|nope|not)\b", re.IGNORECASE),
        }
        # More advanced NLP features can be added here later

    def parse_message(self, message_text: str) -> dict:
        """
        Parses a message to identify commands, intents, and entities.
        Returns a dictionary with parsing results.
        """
        message_text = message_text.strip()

        # Check for commands
        command_match = self.command_pattern.match(message_text)
        if command_match:
            command = command_match.group(1)
            args_str = command_match.group(2).strip()
            # Simple space-based argument splitting
            args = [arg for arg in args_str.split(' ') if arg]
            return {
                "type": "command",
                "command": command,
                "args": args,
                "raw_text": message_text
            }

        # Check for intents
        detected_intents = []
        for intent, pattern in self.intent_patterns.items():
            if pattern.search(message_text):
                detected_intents.append(intent)

        if detected_intents:
            # For now, just return the first detected intent if multiple
            # More sophisticated disambiguation might be needed later
            return {
                "type": "intent",
                "intent": detected_intents[0] if detected_intents else "unknown",
                "entities": self._extract_entities(message_text), # Placeholder for entity extraction
                "raw_text": message_text,
                "all_detected_intents": detected_intents
            }

        # Default: treat as a generic message
        return {
            "type": "message",
            "intent": "unknown",
            "entities": self._extract_entities(message_text), # Placeholder for entity extraction
            "raw_text": message_text
        }

    def _extract_entities(self, message_text: str) -> dict:
        """
        Placeholder for entity extraction logic.
        Currently returns an empty dict.
        """
        # TODO: Implement more sophisticated entity extraction
        # For example, using regex for dates, numbers, names, or a library like spaCy/NLTK.
        entities = {}
        # Example: extract numbers
        numbers = re.findall(r"\b\d+\b", message_text)
        if numbers:
            entities["numbers"] = numbers
        return entities

if __name__ == '__main__':
    # Example Usage
    parser = NLPParser()

    test_messages = [
        "/start",
        "/greet John Doe",
        "Hello there!",
        "Yes, I think so.",
        "Can you help me with task 123?",
        "goodbye friend",
        "I need to set a reminder for tomorrow at 10am"
    ]

    for msg in test_messages:
        parsed_result = parser.parse_message(msg)
        print(f"Original: '{msg}'")
        print(f"Parsed: {parsed_result}\n")

    # Test specific entity extraction
    print("Entity extraction test:")
    result_entities = parser.parse_message("I need 3 apples and 5 oranges for 2 people.")
    print(f"Original: 'I need 3 apples and 5 oranges for 2 people.'")
    print(f"Parsed: {result_entities}\n")

    result_entities_command = parser.parse_message("/process_order item_id_123 quantity 5 user_456")
    print(f"Original: '/process_order item_id_123 quantity 5 user_456'")
    print(f"Parsed: {result_entities_command}\n")

    result_empty_command = parser.parse_message("/status")
    print(f"Original: '/status'")
    print(f"Parsed: {result_empty_command}\n")
