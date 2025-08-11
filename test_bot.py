import unittest
from unittest.mock import MagicMock, patch, call, AsyncMock
import json
import asyncio

# Assuming bot.py is in the same directory or accessible in PYTHONPATH
import bot
import telebot
from katana.fsm.context import FSMContext
from katana.commands.default_commands import IdleState
from katana.commands.cleanup_command import CleanupConfirmationState


class TestBotIntegration(unittest.IsolatedAsyncioTestCase):
    """
    Tests the integration of the FSM with the bot's message processing loop.
    """

    def setUp(self):
        # Mock the bot instance and its methods
        self.mock_bot_instance = MagicMock(spec=telebot.async_telebot.AsyncTeleBot)
        self.mock_bot_instance.reply_to = AsyncMock()
        self.bot_patcher = patch("bot.bot", self.mock_bot_instance)
        self.bot_patcher.start()

        # Mock the FSM manager and its methods
        self.mock_fsm_manager = MagicMock()
        self.mock_fsm_manager.handle_event = AsyncMock()
        self.fsm_manager_patcher = patch("bot.fsm_manager", self.mock_fsm_manager)
        self.fsm_manager_patcher.start()

        # Mock the KatanaAgent
        self.mock_katana_agent = MagicMock()
        self.mock_katana_agent.get_response = MagicMock(return_value="Katana says hi")
        self.katana_agent_patcher = patch(
            "bot.katana_agent_instance", self.mock_katana_agent
        )
        self.katana_agent_patcher.start()

        # Patch logging to avoid clutter
        self.log_patcher = patch("bot.log_local_bot_event")
        self.log_patcher.start()

        # Clear any leftover FSMs from previous runs in the actual manager
        # This is important if the manager is a singleton and tests run in the same process
        from katana.fsm.manager import fsm_manager
        fsm_manager.fsms.clear()

    def tearDown(self):
        self.bot_patcher.stop()
        self.fsm_manager_patcher.stop()
        self.katana_agent_patcher.stop()
        self.log_patcher.stop()

    def _create_mock_message(self, text):
        mock_message = MagicMock(spec=telebot.types.Message)
        mock_message.chat = MagicMock(spec=telebot.types.Chat)
        mock_message.chat.id = 123
        mock_message.text = text
        return mock_message

    async def test_json_command_is_routed_to_fsm(self):
        """Test that a valid JSON string is parsed and sent to the FSM."""
        command = {
            "type": "exec",
            "module": "system",
            "args": {"command": "ps"},
            "id": "test_exec",
        }
        json_command = json.dumps(command)
        mock_message = self._create_mock_message(json_command)

        with patch("bot.interpret", return_value=None):
            await bot.process_user_message(
                mock_message.chat.id, mock_message.text, mock_message
            )

        # Assert that the FSM manager was called
        self.mock_fsm_manager.handle_event.assert_called_once()
        # Check the arguments passed to handle_event
        args, _ = self.mock_fsm_manager.handle_event.call_args
        context, event = args
        self.assertIsInstance(context, FSMContext)
        self.assertEqual(context.chat_id, mock_message.chat.id)
        self.assertEqual(event, command)

    async def test_plain_text_is_routed_to_katana_agent_when_fsm_is_idle(self):
        """Test that plain text is routed to KatanaAgent if the FSM is idle."""
        mock_message = self._create_mock_message("hello world")

        # Configure the mock manager to simulate that no FSM exists for this chat
        self.mock_fsm_manager.fsms.get.return_value = None

        with patch("bot.interpret", return_value=None):
            await bot.process_user_message(
                mock_message.chat.id, mock_message.text, mock_message
            )

        # FSM should not be called for plain text in idle state
        self.mock_fsm_manager.handle_event.assert_not_called()
        # KatanaAgent should be called instead
        self.mock_katana_agent.get_response.assert_called_once()
        self.mock_bot_instance.reply_to.assert_called_once_with(
            mock_message, "Katana says hi"
        )

    async def test_plain_text_is_routed_to_fsm_when_fsm_is_active(self):
        """Test that plain text is routed to the FSM if it's in an active state."""
        mock_message = self._create_mock_message("yes")
        chat_id = mock_message.chat.id

        # Manually set up the FSM to be in an active state for this chat
        from katana.fsm.manager import fsm_manager
        from katana.fsm.machine import FiniteStateMachine

        fsm = FiniteStateMachine(IdleState)
        fsm.current_state = CleanupConfirmationState(fsm) # Put it in an active state
        fsm_manager.fsms[chat_id] = fsm

        with patch("bot.interpret", return_value=None):
            await bot.process_user_message(
                chat_id, mock_message.text, mock_message
            )

        # FSM manager should be called with a text_message event
        self.mock_fsm_manager.handle_event.assert_called_once()
        args, _ = self.mock_fsm_manager.handle_event.call_args
        context, event = args
        self.assertEqual(event, {"type": "text_message", "text": "yes"})
        # KatanaAgent should NOT be called
        self.mock_katana_agent.get_response.assert_not_called()

    async def test_cleanup_command_e2e_flow(self):
        """Perform an end-to-end test of the /cleanup command flow."""
        # We are not mocking the FSM manager anymore, but testing its interaction with the bot
        self.fsm_manager_patcher.stop()

        chat_id = 456

        # 1. User sends /cleanup
        cleanup_message = self._create_mock_message("/cleanup")
        cleanup_message.chat.id = chat_id
        await bot.command_cleanup_impl(cleanup_message)

        # Bot should have asked for confirmation
        self.mock_bot_instance.reply_to.assert_called_once()
        self.assertIn("Are you sure", self.mock_bot_instance.reply_to.call_args[0][1])

        # 2. User sends "yes"
        self.mock_bot_instance.reply_to.reset_mock()
        yes_message = self._create_mock_message("yes")
        yes_message.chat.id = chat_id

        # Mock run_katana_command for the cleanup action
        with patch('bot.run_katana_command', new_callable=AsyncMock, return_value="Success") as mock_run:
            await bot.process_user_message(chat_id, yes_message.text, yes_message)

            # Check that the cleanup command was executed
            mock_run.assert_called_once_with("find voice_temp -type f -delete")

        # Check that the bot sent the correct sequence of replies
        self.assertEqual(self.mock_bot_instance.reply_to.call_count, 3)
        self.mock_bot_instance.reply_to.assert_has_calls([
            call(yes_message, "✅ Confirmation received. Proceeding with cleanup."),
            call(yes_message, "🧹 Performing cleanup of temporary files..."),
            call(yes_message, "✅ Cleanup complete.\n\nOutput:\n`Success`"),
        ])

        # Restore the patcher we stopped
        self.fsm_manager_patcher.start()

if __name__ == "__main__":
    unittest.main()
