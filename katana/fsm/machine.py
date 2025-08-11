from typing import Type, Any
from .state import State
from .context import FSMContext
import logging

log = logging.getLogger(__name__)


class FiniteStateMachine:
    """An asynchronous Finite State Machine."""

    def __init__(self, initial_state_class: Type[State]):
        """
        Initializes the Finite State Machine.

        Args:
            initial_state_class: The class of the initial state for the FSM.
        """
        self.current_state: State | None = None
        self._initial_state_class = initial_state_class
        log.info(f"FSM initialized with initial state class {initial_state_class.__name__}.")

    async def _initialize_fsm(self, context: FSMContext) -> None:
        """Initializes or resets the FSM to its initial state."""
        if self.current_state:
            log.info(f"Exiting state: {self.current_state.__class__.__name__}")
            await self.current_state.on_exit(context)

        log.info(f"Entering initial state: {self._initial_state_class.__name__}")
        self.current_state = self._initial_state_class(self)
        await self.current_state.on_enter(context)

    async def transition_to(
        self, context: FSMContext, new_state_class: Type[State], payload: Any = None
    ) -> None:
        """
        Transitions the FSM to a new state.

        Args:
            context: The context object providing access to bot functions.
            new_state_class: The class of the new state to transition to.
            payload: Optional data to pass to the new state's on_enter method.
        """
        if self.current_state:
            log.info(f"Exiting state: {self.current_state.__class__.__name__}")
            await self.current_state.on_exit(context)

        log.info(f"Entering state: {new_state_class.__name__}")
        self.current_state = new_state_class(self)
        await self.current_state.on_enter(context, payload)

    async def handle_event(self, context: FSMContext, event: dict) -> None:
        """
        Delegates event handling to the current state.
        If the FSM has not been initialized, it will be initialized first.
        """
        if not self.current_state:
            log.info("FSM has not been initialized. Initializing to starting state.")
            await self._initialize_fsm(context)

        # Now that we are guaranteed to have a state, handle the event.
        if self.current_state:
            log.info(f"Handling event in state {self.current_state.__class__.__name__}")
            await self.current_state.handle_event(context, event)

    async def reset(self, context: FSMContext) -> None:
        """Resets the FSM to its initial state."""
        log.info("Resetting FSM to initial state.")
        await self._initialize_fsm(context)
