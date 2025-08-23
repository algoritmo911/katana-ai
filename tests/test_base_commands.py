# tests/test_base_commands.py
import pytest
from unittest.mock import AsyncMock
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.commands.base_commands import handle_ping

@pytest.mark.asyncio
async def test_ping_command():
    """Tests that the /ping command handler responds with 'pong'."""
    # Mock the message object and its methods
    message_mock = AsyncMock()

    # Call the handler directly
    await handle_ping(message=message_mock)

    # Assert that the answer method was called once with "pong"
    message_mock.answer.assert_called_once_with("pong")
