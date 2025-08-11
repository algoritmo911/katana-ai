import unittest
from unittest.mock import AsyncMock, MagicMock, call

# Adjust imports for project structure
from katana.fsm.context import FSMContext
from katana.commands.default_commands import (
    IdleState,
    ExecState,
    InfoState,
    StopState,
    JSON_COMMAND_MAP,
    SLASH_COMMAND_MAP,
)
from katana.commands.cleanup_command import (
    CleanupConfirmationState,
    PerformingCleanupState,
)


class TestCommandStates(unittest.IsolatedAsyncioTestCase):
    """Tests for the individual FSM command states."""

    def setUp(self):
        # Mock FSM instance that states can interact with
        self.mock_fsm = MagicMock()
        self.mock_fsm.transition_to = AsyncMock()
        self.mock_fsm.reset = AsyncMock()

        # Mock context object
        self.mock_context = MagicMock(spec=FSMContext)
        self.mock_context.chat_id = 123
        self.mock_context.reply = AsyncMock()
        self.mock_context.execute = AsyncMock()

    async def test_idle_state_routes_json_command(self):
        """Test IdleState correctly routes a JSON command like 'exec'."""
        idle_state = IdleState(self.mock_fsm)
        exec_event = {
            "type": "exec",
            "module": "system",
            "args": {"command": "ls"},
            "id": "test1",
        }

        await idle_state.handle_event(self.mock_context, exec_event)

        # It should transition to ExecState, passing the event as payload
        self.mock_fsm.transition_to.assert_called_once_with(
            self.mock_context, ExecState, payload=exec_event
        )

    async def test_idle_state_routes_slash_command(self):
        """Test IdleState correctly routes a slash command like '/cleanup'."""
        idle_state = IdleState(self.mock_fsm)
        cleanup_event = {"type": "slash_command", "command": "cleanup"}

        await idle_state.handle_event(self.mock_context, cleanup_event)

        # It should transition to CleanupConfirmationState
        self.mock_fsm.transition_to.assert_called_once_with(
            self.mock_context, CleanupConfirmationState, payload=cleanup_event
        )

    async def test_exec_state_executes_and_transitions(self):
        """Test ExecState executes a command and transitions back to IdleState."""
        exec_state = ExecState(self.mock_fsm)
        exec_payload = {
            "type": "exec",
            "args": {"command": "ls -l"},
        }
        self.mock_context.execute.return_value = "file1.txt"

        # The logic is in on_enter for one-shot commands
        await exec_state.on_enter(self.mock_context, payload=exec_payload)

        # Check that the command was executed
        self.mock_context.execute.assert_called_once_with("ls -l")
        # Check that it replied to the user
        self.mock_context.reply.assert_has_calls(
            [
                call("⚙️ Executing: `ls -l`", parse_mode="Markdown"),
                call("file1.txt"),
            ]
        )
        # Check that it transitioned back to Idle
        self.mock_fsm.transition_to.assert_called_once_with(self.mock_context, IdleState)

    async def test_cleanup_confirmation_state_sends_prompt(self):
        """Test CleanupConfirmationState sends the confirmation prompt on entry."""
        state = CleanupConfirmationState(self.mock_fsm)
        await state.on_enter(self.mock_context, payload={})

        self.mock_context.reply.assert_called_once()
        # Check that the reply contains the expected prompt text
        self.assertIn("Are you sure", self.mock_context.reply.call_args[0][0])
        self.assertIn("yes", self.mock_context.reply.call_args[0][0])

    async def test_cleanup_confirmation_state_handles_yes(self):
        """Test CleanupConfirmationState transitions to PerformingCleanupState on 'yes'."""
        state = CleanupConfirmationState(self.mock_fsm)
        event = {"type": "text_message", "text": "  YeS  "}  # Test with whitespace/case

        await state.handle_event(self.mock_context, event)

        self.mock_context.reply.assert_called_once_with(
            "✅ Confirmation received. Proceeding with cleanup."
        )
        self.mock_fsm.transition_to.assert_called_once_with(
            self.mock_context, PerformingCleanupState
        )

    async def test_cleanup_confirmation_state_handles_no(self):
        """Test CleanupConfirmationState transitions back to IdleState on other text."""
        state = CleanupConfirmationState(self.mock_fsm)
        event = {"type": "text_message", "text": "no thank you"}

        await state.handle_event(self.mock_context, event)

        self.mock_context.reply.assert_called_once_with("❌ Cleanup cancelled.")
        self.mock_fsm.transition_to.assert_called_once_with(self.mock_context, IdleState)

    async def test_performing_cleanup_state(self):
        """Test PerformingCleanupState executes the command and transitions."""
        state = PerformingCleanupState(self.mock_fsm)
        self.mock_context.execute.return_value = "cleaned 0 files"

        await state.on_enter(self.mock_context, payload={})

        self.mock_context.execute.assert_called_once_with(
            "find voice_temp -type f -delete"
        )
        self.mock_context.reply.assert_has_calls(
            [
                call("🧹 Performing cleanup of temporary files..."),
                call("✅ Cleanup complete.\n\nOutput:\n`cleaned 0 files`"),
            ]
        )
        self.mock_fsm.transition_to.assert_called_once_with(self.mock_context, IdleState)


if __name__ == "__main__":
    unittest.main()
