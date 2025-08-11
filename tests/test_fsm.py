import unittest
from unittest.mock import AsyncMock, MagicMock

# Adjust imports based on the actual project structure
from katana.fsm.machine import FiniteStateMachine
from katana.fsm.state import State
from katana.fsm.manager import FSMManager
from katana.fsm.context import FSMContext


class TestFSM(unittest.IsolatedAsyncioTestCase):
    """Tests for the Finite State Machine core components."""

    def setUp(self):
        # Create a mock context object that can be passed to FSM methods
        self.mock_context = MagicMock(spec=FSMContext)
        self.mock_context.reply = AsyncMock()
        self.mock_context.execute = AsyncMock()
        self.mock_context.chat_id = 123

    async def test_fsm_lazy_initialization(self):
        """Test that the FSM initializes and enters the first state only on the first event."""
        # Create mock state classes
        mock_state_enter = AsyncMock()
        mock_state_exit = AsyncMock()

        class MockState(State):
            async def on_enter(self, context, payload=None):
                await mock_state_enter(payload)

            async def on_exit(self, context):
                await mock_state_exit()

            async def handle_event(self, context, event):
                pass

        fsm = FiniteStateMachine(initial_state_class=MockState)
        # Initially, no state should be entered
        self.assertIsNone(fsm.current_state)
        mock_state_enter.assert_not_called()

        # The first event should trigger initialization
        first_event = {"type": "start"}
        await fsm.handle_event(self.mock_context, first_event)

        # Now the state should be entered
        self.assertIsInstance(fsm.current_state, MockState)
        # on_enter is now called without a payload during initialization
        mock_state_enter.assert_called_once_with(None)
        mock_state_exit.assert_not_called()  # Nothing has been exited yet

    async def test_fsm_transition(self):
        """Test the state transition logic."""
        # Mock state classes with mocked methods
        state1_enter = AsyncMock()
        state1_exit = AsyncMock()
        state2_enter = AsyncMock()
        state2_exit = AsyncMock()  # Not expected to be called in this test

        class State1(State):
            async def on_enter(self, context, payload=None):
                await state1_enter(payload)

            async def on_exit(self, context):
                await state1_exit()

            async def handle_event(self, context, event):
                # This state transitions on any event
                await self.fsm.transition_to(context, State2, payload="from_state1")

        class State2(State):
            async def on_enter(self, context, payload=None):
                await state2_enter(payload)

            async def on_exit(self, context):
                await state2_exit()

            async def handle_event(self, context, event):
                pass

        fsm = FiniteStateMachine(initial_state_class=State1)
        # Initialize the FSM and trigger the first transition all in one go
        await fsm.handle_event(self.mock_context, {"type": "init"})

        # Check the sequence of events
        # The first event initializes the FSM to State1, which then immediately
        # handles the event and transitions to State2.
        state1_enter.assert_called_once_with(None)
        state1_exit.assert_called_once()
        state2_enter.assert_called_once_with("from_state1")
        self.assertIsInstance(fsm.current_state, State2)

    async def test_fsm_manager(self):
        """Test that the FSM manager creates and reuses FSMs correctly."""
        manager = FSMManager()
        chat_id_1 = 111
        chat_id_2 = 222

        # Mock context for chat 1
        context1 = MagicMock(spec=FSMContext)
        context1.chat_id = chat_id_1

        # Mock context for chat 2
        context2 = MagicMock(spec=FSMContext)
        context2.chat_id = chat_id_2

        # First event for chat 1 should create an FSM
        self.assertNotIn(chat_id_1, manager.fsms)
        await manager.handle_event(context1, {"type": "event1"})
        self.assertIn(chat_id_1, manager.fsms)
        fsm1_instance = manager.fsms[chat_id_1]

        # Second event for chat 1 should reuse the same FSM
        await manager.handle_event(context1, {"type": "event2"})
        self.assertIs(manager.fsms[chat_id_1], fsm1_instance)

        # First event for chat 2 should create a new FSM
        self.assertNotIn(chat_id_2, manager.fsms)
        await manager.handle_event(context2, {"type": "event3"})
        self.assertIn(chat_id_2, manager.fsms)
        fsm2_instance = manager.fsms[chat_id_2]

        # The two FSMs should be different instances
        self.assertIsNot(fsm1_instance, fsm2_instance)


if __name__ == "__main__":
    unittest.main()
