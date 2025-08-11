from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .machine import FiniteStateMachine
    from .context import FSMContext


class State(ABC):
    """
    An abstract base class for a state in an asynchronous Finite State Machine.
    """

    def __init__(self, fsm: "FiniteStateMachine"):
        """
        Initializes the state.

        Args:
            fsm: The FiniteStateMachine instance that this state belongs to.
        """
        self.fsm = fsm

    async def on_enter(self, context: "FSMContext", payload: Any = None) -> None:
        """
        Called when this state is entered.
        An optional payload can be passed from the previous state during a transition.

        Args:
            context: The context object providing access to bot functions.
            payload: Optional data from the previous state.
        """
        pass

    async def on_exit(self, context: "FSMContext") -> None:
        """
        Called when this state is exited, before the new state is entered.

        Args:
            context: The context object providing access to bot functions.
        """
        pass

    @abstractmethod
    async def handle_event(self, context: "FSMContext", event: dict) -> None:
        """
        Handles an incoming event.

        This method is responsible for processing the event and potentially
        triggering a transition to a new state by calling `self.fsm.transition_to()`.

        Args:
            context: The context object providing access to bot functions.
            event: A dictionary representing the event to handle.
        """
        pass
