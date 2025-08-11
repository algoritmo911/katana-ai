import logging
from typing import Type, Dict

from katana.fsm.state import State
from katana.fsm.context import FSMContext
from katana.commands.cleanup_command import CleanupConfirmationState

# Configure logging
log = logging.getLogger(__name__)


# Forward-declare IdleState so other states can reference it for transitions.
class IdleState:
    pass


class ExecState(State):
    """A state to handle the 'exec' command."""

    async def handle_event(self, context: FSMContext, event: dict) -> None:
        # This state acts on entry and should not handle subsequent events.
        log.warning(f"{self.__class__.__name__} received an unexpected event: {event}")

    async def on_enter(self, context: FSMContext, payload: dict) -> None:
        """
        On entering the state, execute the command from the payload
        and then immediately transition back to the IdleState.
        """
        log.info(f"Entering ExecState for chat {context.chat_id}")
        command = payload.get("args", {}).get("command")

        if not command:
            await context.reply("⚠️ 'exec' command type requires a 'command' in args.")
        else:
            try:
                await context.reply(f"⚙️ Executing: `{command}`", parse_mode="Markdown")
                output = await context.execute(command)
                await context.reply(output)
            except Exception as e:
                log.error(f"Error executing command '{command}': {e}")
                await context.reply(f"An error occurred: {e}")

        # Transition back to the idle state after the command is done.
        await self.fsm.transition_to(context, IdleState)


class InfoState(State):
    """A state to handle the 'info' command."""

    async def handle_event(self, context: FSMContext, event: dict) -> None:
        # This state acts on entry and should not handle subsequent events.
        log.warning(f"{self.__class__.__name__} received an unexpected event: {event}")

    async def on_enter(self, context: FSMContext, payload: dict) -> None:
        log.info(f"Entering InfoState for chat {context.chat_id}")
        info_text = payload.get("args", {}).get("text", "No info provided.")
        await context.reply(f"ℹ️ {info_text}")
        await self.fsm.transition_to(context, IdleState)


class RepeatState(State):
    """A state to handle the 'repeat' command."""

    async def handle_event(self, context: FSMContext, event: dict) -> None:
        # This state acts on entry and should not handle subsequent events.
        log.warning(f"{self.__class__.__name__} received an unexpected event: {event}")

    async def on_enter(self, context: FSMContext, payload: dict) -> None:
        log.info(f"Entering RepeatState for chat {context.chat_id}")
        # In a real implementation, this would require access to command history.
        await context.reply("🔁 Repeating last action (placeholder).")
        await self.fsm.transition_to(context, IdleState)


class StopState(State):
    """A state to handle the 'stop' command."""

    async def handle_event(self, context: FSMContext, event: dict) -> None:
        # This state acts on entry and should not handle subsequent events.
        log.warning(f"{self.__class__.__name__} received an unexpected event: {event}")

    async def on_enter(self, context: FSMContext, payload: dict) -> None:
        """
        For now, 'stop' will reset the FSM for the user to the initial state.
        This is a clean way to terminate any multi-step command sequence.
        """
        log.info(f"Entering StopState for chat {context.chat_id}. Resetting FSM.")
        await context.reply("🛑 Stopping current action and resetting state.")
        # The 'reset' method handles the transition back to the initial state.
        await self.fsm.reset(context)


# --- The main router state ---

JSON_COMMAND_MAP: Dict[str, Type[State]] = {
    "exec": ExecState,
    "info": InfoState,
    "repeat": RepeatState,
    "stop": StopState,
}

SLASH_COMMAND_MAP: Dict[str, Type[State]] = {
    "cleanup": CleanupConfirmationState,
}


class IdleState(State):
    """
    The default state for the FSM, waiting for a command.
    It acts as a router to other states based on the event type.
    """

    async def handle_event(self, context: FSMContext, event: dict) -> None:
        """
        Parses the event and transitions to the appropriate state.
        Handles different event structures (e.g., JSON commands, slash commands).
        """
        event_type = event.get("type")
        log.info(
            f"IdleState for chat {context.chat_id} handling event with type: {event_type}"
        )

        target_state_class = None
        if event_type in JSON_COMMAND_MAP:
            # Legacy JSON commands use the 'type' field directly as the command
            target_state_class = JSON_COMMAND_MAP.get(event_type)
        elif event_type == "slash_command":
            command_name = event.get("command")
            target_state_class = SLASH_COMMAND_MAP.get(command_name)

        if target_state_class:
            # Transition to the state that will handle the command,
            # passing the original event as a payload for that state to use.
            await self.fsm.transition_to(context, target_state_class, payload=event)
        else:
            # If the event is not recognized, inform the user.
            # This could be a text message that was not handled by other logic.
            log.warning(f"IdleState received an unhandled event type: {event_type}")
            # We can choose to reply or stay silent. Let's stay silent for now
            # to avoid replying to every random message.
            # await context.reply(f"Error: Unrecognized command or event '{event_type}'.")
