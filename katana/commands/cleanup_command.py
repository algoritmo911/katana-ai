import logging

from typing import TYPE_CHECKING
from katana.fsm.state import State
from katana.fsm.context import FSMContext

if TYPE_CHECKING:
    from katana.commands.default_commands import IdleState

log = logging.getLogger(__name__)


class PerformingCleanupState(State):
    """A state that performs the actual cleanup action."""

    async def handle_event(self, context: FSMContext, event: dict) -> None:
        # This state acts on entry and should not handle subsequent events.
        log.warning(f"{self.__class__.__name__} received an unexpected event: {event}")

    async def on_enter(self, context: FSMContext, payload: dict) -> None:
        log.info(f"Entering PerformingCleanupState for chat {context.chat_id}")
        await context.reply("🧹 Performing cleanup of temporary files...")
        try:
            # This is a safe command to remove files only inside voice_temp directory.
            # It avoids using 'rm -rf' directly for safety.
            cleanup_command = "find voice_temp -type f -delete"
            output = await context.execute(cleanup_command)
            if not output:
                output = "No files to delete."
            await context.reply(f"✅ Cleanup complete.\n\nOutput:\n`{output}`")
        except Exception as e:
            log.error(f"Error during cleanup for chat {context.chat_id}: {e}")
            await context.reply(f"⚠️ An error occurred during cleanup: {e}")

        from katana.commands.default_commands import IdleState

        # Always transition back to the idle state.
        await self.fsm.transition_to(context, IdleState)


class CleanupConfirmationState(State):
    """Awaits user confirmation for the cleanup action."""

    async def on_enter(self, context: FSMContext, payload: dict) -> None:
        log.info(f"Entering CleanupConfirmationState for chat {context.chat_id}")
        await context.reply(
            "⚠️ Are you sure you want to delete all temporary voice files? "
            "This action cannot be undone.\n\n"
            "Please reply with `yes` to confirm or anything else to cancel."
        )

    async def handle_event(self, context: FSMContext, event: dict) -> None:
        """
        Handles the user's confirmation response.
        This state expects a plain text message event.
        """
        user_response = event.get("text", "").lower().strip()
        log.info(
            f"CleanupConfirmationState for chat {context.chat_id} received response: '{user_response}'"
        )

        if user_response == "yes":
            await context.reply("✅ Confirmation received. Proceeding with cleanup.")
            await self.fsm.transition_to(context, PerformingCleanupState)
        else:
            from katana.commands.default_commands import IdleState

            await context.reply("❌ Cleanup cancelled.")
            await self.fsm.transition_to(context, IdleState)
