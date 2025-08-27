import asyncio
import unittest

from src.katana.core.handlers import StartCommandHandler, PingCommandHandler
from src.katana.domain.commands import StartCommand, PingCommand

class TestCoreHandlers(unittest.TestCase):

    def test_start_command_handler(self):
        """
        Tests that the StartCommandHandler correctly processes the StartCommand
        and returns a personalized welcome message.
        """
        async def run_test():
            # Arrange: Create an instance of the handler and the command
            handler = StartCommandHandler()
            command = StartCommand(
                user_id=12345,
                user_name="Jules",
                chat_id=67890,
            )

            # Act: Call the handler with the command
            result = await handler.handle(command)

            # Assert: Check if the output is the expected string
            self.assertIn("Welcome, Jules", result)
            self.assertIn("new, modular core", result)

        # Run the async test function
        asyncio.run(run_test())

    def test_ping_command_handler(self):
        """
        Tests that the PingCommandHandler correctly processes the PingCommand
        and returns a simple 'pong'.
        """
        async def run_test():
            # Arrange
            handler = PingCommandHandler()
            command = PingCommand(user_id=12345, chat_id=67890)

            # Act
            result = await handler.handle(command)

            # Assert
            self.assertEqual(result, "pong")

        # Run the async test function
        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()
