import asyncio
import unittest

from src.katana.core.command_bus import CommandBus
from src.katana.core.handlers import StartCommandHandler, PingCommandHandler, CommandHandler
from src.katana.domain.commands import StartCommand, PingCommand, Command

class TestCommandBusIntegration(unittest.TestCase):

    def setUp(self):
        """Set up a new command bus and handlers for each test."""
        self.bus = CommandBus()
        # Register real handlers to test the integration
        self.bus.register(StartCommand, StartCommandHandler())
        self.bus.register(PingCommand, PingCommandHandler())

    def test_dispatch_to_start_handler(self):
        """
        Tests that a StartCommand is correctly dispatched to the StartCommandHandler
        and produces the expected result.
        """
        async def run_test():
            # Arrange
            command = StartCommand(user_id=100, user_name="Test User", chat_id=200)

            # Act
            result = await self.bus.dispatch(command)

            # Assert
            self.assertIn("Welcome, Test User", result)
            self.assertIn("new, modular core", result)

        asyncio.run(run_test())

    def test_dispatch_to_ping_handler(self):
        """
        Tests that a PingCommand is correctly dispatched to the PingCommandHandler
        and returns 'pong'.
        """
        async def run_test():
            # Arrange
            command = PingCommand(user_id=100, chat_id=200)

            # Act
            result = await self.bus.dispatch(command)

            # Assert
            self.assertEqual(result, "pong")

        asyncio.run(run_test())

    def test_dispatching_unregistered_command_raises_error(self):
        """
        Tests that attempting to dispatch a command that has no registered handler
        raises a TypeError, as per the CommandBus's contract.
        """
        # Define a dummy command that is not registered
        class UnregisteredCommand(Command):
            pass

        command = UnregisteredCommand()

        # The test needs to run an async function, so we define one
        async def run_test():
            # Use async with self.assertRaises to test for exceptions in async code
            with self.assertRaises(TypeError):
                await self.bus.dispatch(command)

        asyncio.run(run_test())

    def test_registering_invalid_handler_raises_error(self):
        """
        Tests that registering something that isn't a CommandHandler raises a TypeError.
        """
        class NotAHandler:
            pass

        with self.assertRaises(TypeError):
            self.bus.register(PingCommand, NotAHandler())


if __name__ == "__main__":
    unittest.main()
