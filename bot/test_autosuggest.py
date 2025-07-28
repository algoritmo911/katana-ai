# bot/test_autosuggest.py
import unittest
from bot import autosuggest

class TestAutosuggest(unittest.TestCase):

    def test_get_suggestions_no_context(self):
        """Test that generic suggestions are returned when there is no context."""
        suggestions = autosuggest.get_suggestions({}, [])
        self.assertTrue(len(suggestions) > 0)
        for suggestion in suggestions:
            self.assertIn("text", suggestion)
            self.assertIn("callback_data", suggestion)

    def test_get_suggestions_weather_context(self):
        """Test that weather-related suggestions are returned for weather context."""
        context = {"last_processed_intent": "get_weather"}
        suggestions = autosuggest.get_suggestions(context, [])
        self.assertIn("suggest_weather_new_city", [s["callback_data"] for s in suggestions])

    def test_get_suggestions_joke_context(self):
        """Test that joke-related suggestions are returned for joke context."""
        context = {"last_processed_intent": "tell_joke"}
        suggestions = autosuggest.get_suggestions(context, [])
        self.assertIn("suggest_joke", [s["callback_data"] for s in suggestions])

    def test_get_suggestions_fact_context(self):
        """Test that fact-related suggestions are returned for fact context."""
        context = {"last_processed_intent": "get_fact"}
        suggestions = autosuggest.get_suggestions(context, [])
        self.assertIn("suggest_fact", [s["callback_data"] for s in suggestions])

    def test_get_suggestions_clarify_city_context(self):
        """Test that city clarification suggestions are returned."""
        context = {"last_processed_intent": "clarify_city_for_weather"}
        suggestions = autosuggest.get_suggestions(context, [])
        self.assertIn("suggest_weather_london", [s["callback_data"] for s in suggestions])
        self.assertIn("suggest_cancel_weather", [s["callback_data"] for s in suggestions])

if __name__ == '__main__':
    unittest.main()
