import unittest
from web.utils.session import UserSession

class TestStatePreservation(unittest.TestCase):
    def test_state_preservation(self):
        # Create a user session
        user_session = UserSession()

        # Set a value in the session
        user_session.set("name", "Jules")

        # Get the value from the session
        name = user_session.get("name")

        # Check that the value is correct
        self.assertEqual(name, "Jules")

if __name__ == '__main__':
    unittest.main()
