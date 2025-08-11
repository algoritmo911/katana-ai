import logging
from typing import Dict

from katana.fsm.machine import FiniteStateMachine
from katana.fsm.context import FSMContext
from katana.commands.default_commands import IdleState

log = logging.getLogger(__name__)


class FSMManager:
    """
    Manages all FSM instances for different chats, ensuring each chat
    has its own state machine.
    """

    def __init__(self):
        self.fsms: Dict[int, FiniteStateMachine] = {}
        log.info("FSMManager initialized.")

    def _get_or_create_fsm(self, chat_id: int) -> FiniteStateMachine:
        """
        Retrieves the FSM for a given chat_id. If one does not exist,
        it creates a new one, initialized with IdleState.
        """
        if chat_id not in self.fsms:
            log.info(f"No FSM found for chat {chat_id}. Creating a new one.")
            # Every new FSM for a chat starts in the IdleState.
            self.fsms[chat_id] = FiniteStateMachine(initial_state_class=IdleState)
        return self.fsms[chat_id]

    async def handle_event(self, context: FSMContext, event: dict) -> None:
        """
        The main entry point for processing an event for a given chat.
        It finds the correct FSM and delegates the event handling to it.
        """
        log.debug(f"Handling event for chat {context.chat_id}: {event}")
        fsm = self._get_or_create_fsm(context.chat_id)
        await fsm.handle_event(context, event)


# Create a single, global instance of the manager for the bot to use.
# This makes it easily accessible from the main bot file.
fsm_manager = FSMManager()
