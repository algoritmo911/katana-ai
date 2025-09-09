import logging
import json
from .dsl import Step

logger = logging.getLogger(__name__)

class StrategyInterpreter:
    def __init__(self, agent_id: str, nats_client):
        self.agent_id = agent_id
        self.nats_client = nats_client
        # The dispatch table maps DSL types to handler methods
        self.condition_handlers = {
            "state.is_false": self._handle_condition_state_is_false
        }
        self.action_handlers = {
            "hephaestus.trade": self._handle_action_hephaestus_trade,
            "state.set": self._handle_action_state_set
        }

    async def execute_step(self, step: Step, state: dict) -> bool:
        """
        Executes a single step of a strategy.
        Returns True if the strategy should continue, False if it should stop.
        """
        if step.condition:
            handler = self.condition_handlers.get(step.condition.type)
            if not handler:
                logger.error(f"Unknown condition type: {step.condition.type}")
                return False # Stop execution on unknown condition

            # Conditions return True on success, False on failure.
            # If a condition fails, the strategy execution stops.
            return await handler(step.condition.inputs, state)

        if step.actions:
            for action in step.actions:
                handler = self.action_handlers.get(action.type)
                if not handler:
                    logger.error(f"Unknown action type: {action.type}")
                    continue # Skip unknown actions
                await handler(action.parameters, state)
            return True # Continue execution after actions

        return False # Should not happen with valid DSL

    # --- Condition Handlers ---

    async def _handle_condition_state_is_false(self, inputs: dict, state: dict) -> bool:
        """Checks if a variable in the agent's state is False."""
        variable_name = inputs.get("input", "").replace("state.", "")
        if variable_name not in state:
            logger.warning(f"Condition check on unknown state variable: {variable_name}")
            return False

        is_false = state.get(variable_name) is False
        logger.info(f"Condition 'state.is_false' on '{variable_name}': {is_false}")
        return is_false

    # --- Action Handlers ---

    async def _handle_action_hephaestus_trade(self, parameters: dict, state: dict):
        """Publishes a trade command to Hephaestus."""
        subject = f"agent.{self.agent_id}.action.execute"
        payload = {
            "type": "hephaestus.trade",
            "parameters": parameters # Pass parameters directly
        }
        await self.nats_client.publish(subject, json.dumps(payload).encode())
        logger.info(f"Published 'hephaestus.trade' action to subject '{subject}'")

    async def _handle_action_state_set(self, parameters: dict, state: dict):
        """Sets a variable in the agent's state."""
        variable_name = parameters.get("variable")
        value = parameters.get("value")
        if variable_name:
            state[variable_name] = value
            logger.info(f"Set state variable '{variable_name}' to '{value}'")
