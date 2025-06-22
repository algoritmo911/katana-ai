import unittest
from nlp_providers.base import NLPProvider # For type checking if needed
from nlp_providers.dummy_provider import DummyProvider
from nlp_providers.echo_provider import EchoProvider

class TestDummyProvider(unittest.TestCase):

    def setUp(self):
        self.provider_default_config = DummyProvider()
        self.provider_custom_config = DummyProvider(config={"mode": "custom_test"})

    def test_name(self):
        self.assertEqual(self.provider_default_config.name, "DummyProvider")
        self.assertEqual(self.provider_custom_config.name, "DummyProvider")

    def test_config_passthrough(self):
        self.assertEqual(self.provider_default_config.config, {})
        self.assertEqual(self.provider_custom_config.config, {"mode": "custom_test"})

    def test_get_intent_greeting(self):
        intent = self.provider_default_config.get_intent("Hello bot")
        self.assertEqual(intent["intent_name"], "greeting")
        self.assertGreater(intent["confidence"], 0.8)

    def test_get_intent_weather(self):
        intent = self.provider_default_config.get_intent("what is the weather?")
        self.assertEqual(intent["intent_name"], "get_weather")
        self.assertGreater(intent["confidence"], 0.8)

    def test_get_intent_turn_on_light(self):
        intent = self.provider_default_config.get_intent("turn on the kitchen lamp")
        self.assertEqual(intent["intent_name"], "turn_on_light")
        self.assertGreater(intent["confidence"], 0.8)

    def test_get_intent_book_flight(self):
        intent = self.provider_default_config.get_intent("I want to book a flight")
        self.assertEqual(intent["intent_name"], "book_flight")
        self.assertGreater(intent["confidence"], 0.7) # Slightly lower confidence for more complex phrases maybe

    def test_get_intent_unknown(self):
        intent = self.provider_default_config.get_intent("tell me something random")
        self.assertEqual(intent["intent_name"], "unknown_intent")

    def test_get_slots_weather_location(self):
        slots = self.provider_default_config.get_slots("weather in London", intent="get_weather")
        self.assertEqual(slots.get("location"), "London")

        slots_for = self.provider_default_config.get_slots("weather for Paris", intent="get_weather")
        self.assertEqual(slots_for.get("location"), "Paris")

    def test_get_slots_turn_on_light_device_location(self):
        slots = self.provider_default_config.get_slots("turn on the desk lamp in the office", intent="turn_on_light")
        self.assertEqual(slots.get("device_name"), "desk lamp")
        self.assertEqual(slots.get("location"), "office")

    def test_get_slots_turn_on_light_device_only(self):
        slots = self.provider_default_config.get_slots("turn on ceiling light", intent="turn_on_light")
        self.assertEqual(slots.get("device_name"), "ceiling light")
        self.assertIsNone(slots.get("location"))

    def test_get_slots_book_flight_destination_origin(self):
        slots = self.provider_default_config.get_slots("book a flight to Tokyo from New York", intent="book_flight")
        self.assertEqual(slots.get("destination"), "Tokyo")
        self.assertEqual(slots.get("origin"), "New York")

    def test_get_slots_book_flight_destination_only(self):
        slots = self.provider_default_config.get_slots("book a flight to Berlin", intent="book_flight")
        self.assertEqual(slots.get("destination"), "Berlin")
        self.assertIsNone(slots.get("origin"))

    def test_get_slots_book_flight_origin_only(self):
        slots = self.provider_default_config.get_slots("book a flight from Amsterdam", intent="book_flight")
        self.assertEqual(slots.get("origin"), "Amsterdam")
        self.assertIsNone(slots.get("destination"))

    def test_get_slots_numbers(self):
        slots = self.provider_default_config.get_slots("order 2 pizzas and 1 coke", intent="order_food") # Fictional intent
        self.assertEqual(slots.get("numbers"), [2, 1])

    def test_process_method(self):
        result = self.provider_default_config.process("Hi, what's the weather in Berlin?")
        self.assertEqual(result["intent"]["intent_name"], "get_weather") # Hi might make it greeting, but weather should be stronger
        self.assertEqual(result["slots"].get("location"), "Berlin")


class TestEchoProvider(unittest.TestCase):

    def setUp(self):
        self.provider_default = EchoProvider()
        self.provider_custom_prefix = EchoProvider(config={"prefix": "Echoed: "})

    def test_name(self):
        self.assertEqual(self.provider_default.name, "EchoProvider")

    def test_config_and_prefix(self):
        self.assertEqual(self.provider_default.prefix, "")
        self.assertEqual(self.provider_custom_prefix.prefix, "Echoed: ")

    def test_get_intent(self):
        intent = self.provider_default.get_intent("any text here")
        self.assertEqual(intent["intent_name"], "echo")
        self.assertEqual(intent["confidence"], 1.0)

    def test_get_slots_default_prefix(self):
        text = "this is a test"
        slots = self.provider_default.get_slots(text)
        self.assertEqual(slots.get("echoed_text"), text)

    def test_get_slots_custom_prefix(self):
        text = "another test message"
        slots = self.provider_custom_prefix.get_slots(text)
        self.assertEqual(slots.get("echoed_text"), f"Echoed: {text}")

    def test_process_method_default_prefix(self):
        text = "process this"
        result = self.provider_default.process(text)
        self.assertEqual(result["intent"]["intent_name"], "echo")
        self.assertEqual(result["slots"]["echoed_text"], text)

    def test_process_method_custom_prefix(self):
        text = "process this too"
        result = self.provider_custom_prefix.process(text)
        self.assertEqual(result["intent"]["intent_name"], "echo")
        self.assertEqual(result["slots"]["echoed_text"], f"Echoed: {text}")


if __name__ == '__main__':
    unittest.main()
