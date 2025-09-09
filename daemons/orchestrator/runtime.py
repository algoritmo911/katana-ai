import asyncio
import logging
from .dsl import AgentDefinition
from .interpreter import StrategyInterpreter

logger = logging.getLogger(__name__)

class AgentRuntime:
    def __init__(self, agent_def: AgentDefinition, nats_client):
        self.agent_def = agent_def
        self.nats_client = nats_client
        self.agent_id = agent_def.metadata.name
        self.state = {key: var.initialValue for key, var in agent_def.spec.state.items()}
        self.interpreter = StrategyInterpreter(self.agent_id, self.nats_client)
        self.main_task = None
        self.subscriptions = []

    async def start(self):
        """Starts the agent's main loop and subscribes to triggers."""
        if self.main_task:
            logger.warning(f"Agent '{self.agent_id}' is already running.")
            return

        logger.info(f"Starting runtime for agent '{self.agent_id}'...")
        self.main_task = asyncio.create_task(self._main_loop())

    async def stop(self):
        """Stops the agent's main loop and unsubscribes from triggers."""
        logger.info(f"Stopping runtime for agent '{self.agent_id}'...")
        for sub in self.subscriptions:
            await sub.unsubscribe()
        if self.main_task:
            self.main_task.cancel()
            try:
                await self.main_task
            except asyncio.CancelledError:
                pass
        logger.info(f"Runtime for agent '{self.agent_id}' stopped.")

    async def _main_loop(self):
        """The main execution loop for the agent."""
        # Subscribe to all triggers defined in the DSL
        for trigger in self.agent_def.spec.triggers:
            try:
                sub = await self.nats_client.subscribe(
                    trigger.on,
                    cb=self._make_trigger_handler(trigger.evaluates)
                )
                self.subscriptions.append(sub)
                logger.info(f"Agent '{self.agent_id}' subscribed to trigger '{trigger.on}'")
            except Exception as e:
                logger.error(f"Agent '{self.agent_id}' failed to subscribe to '{trigger.on}': {e}")

        # Keep the task alive to listen for NATS messages
        while True:
            await asyncio.sleep(60)

    def _make_trigger_handler(self, strategy_name: str):
        """Creates a callback handler for a specific trigger."""
        async def handler(msg):
            logger.info(f"Agent '{self.agent_id}' triggered by '{msg.subject}' for strategy '{strategy_name}'")
            strategy = self.agent_def.spec.strategy.get(strategy_name)
            if not strategy:
                logger.error(f"Strategy '{strategy_name}' not found for agent '{self.agent_id}'")
                return

            # Execute strategy steps sequentially
            for step in strategy.steps:
                should_continue = await self.interpreter.execute_step(step, self.state)
                if not should_continue:
                    logger.info(f"Strategy '{strategy_name}' execution stopped by a condition.")
                    break
        return handler
