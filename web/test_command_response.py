import unittest
from web.agents.psy_bot import PsyBot

class TestCommandResponse(unittest.TestCase):
    def test_command_response(self):
        # Create a PsyBot
        psy_bot = PsyBot()

        # Get a response
        response = psy_bot.get_response("I am feeling sad")

        # Check that the response is correct
        self.assertEqual(response, "PsyBot senses you are feeling sad.")

if __name__ == '__main__':
    unittest.main()
