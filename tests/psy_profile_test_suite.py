import unittest
import json
from katana.bots.psy_bot_template import PsyBot

class PsyBotTestSuite(unittest.TestCase):

    def test_psy_bot_creation(self):
        bot = PsyBot()
        self.assertEqual(bot.name, "PsyBot")
        self.assertEqual(bot.mood, "neutral")

    def test_psy_bot_handle_message(self):
        bot = PsyBot()
        response = bot.handle_message("I'm feeling sad.")
        self.assertIn("You said 'I'm feeling sad.'", response)

    def test_psy_bot_profile_loading(self):
        profile = {
            "name": "Dr. Feelgood",
            "initial_mood": "happy"
        }
        with open("test_profile.json", "w") as f:
            json.dump(profile, f)

        bot = PsyBot()
        bot.load_profile("test_profile.json")
        self.assertEqual(bot.name, "Dr. Feelgood")
        self.assertEqual(bot.mood, "happy")

    def test_psy_bot_cloning(self):
        bot1 = PsyBot(bot_name="Bot1")
        bot2 = bot1.clone("Bot2")
        self.assertEqual(bot2.name, "Bot2")
        self.assertEqual(bot1.profile, bot2.profile)

if __name__ == '__main__':
    unittest.main()
