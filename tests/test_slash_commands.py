import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from katana.commands.slash_commands import SlashCommandRegistry

@pytest.fixture
def registry():
    return SlashCommandRegistry()

def test_register_and_execute_command(registry):
    async def test_logic():
        # Mock the async function to be registered
        mock_command_func = AsyncMock()

        # Register a new command
        registry.register("/test", description="A test command")(mock_command_func)

        # Mock the bot and message objects
        mock_bot = MagicMock()
        mock_message = MagicMock()

        # Execute the command
        await registry.execute("/test", 123, "test_args", mock_bot, mock_message)

        # Assert that the mock function was called with the correct arguments
        mock_command_func.assert_called_once_with(123, "test_args", mock_bot, mock_message)

    asyncio.run(test_logic())

def test_unknown_command(registry):
    async def test_logic():
        # Mock the bot and message objects
        mock_bot = MagicMock()
        # Need to mock the reply_to method on the bot object
        mock_bot.reply_to = AsyncMock()
        mock_message = MagicMock()

        # Execute a command that is not registered
        await registry.execute("/unknown", 123, "test_args", mock_bot, mock_message)

        # Assert that the bot replied with an "Unknown command" message
        mock_bot.reply_to.assert_called_once_with(mock_message, "Unknown command: /unknown")

    asyncio.run(test_logic())
