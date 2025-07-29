import logging
from katana.message_dispatcher import MessageDispatcher

logger = logging.getLogger(__name__)


class SignalHub:
    def __init__(self):
        self.dispatcher = MessageDispatcher()

    async def route_signal(self, source, user_id, message, criticality="low"):
        logger.info(
            f"Signal received from {source} for user {user_id} with criticality {criticality}"
        )

        if criticality == "high":
            self.notify_operator(
                f"High criticality signal from {source} for user {user_id}: {message}"
            )

        return await self.dispatcher.dispatch(source, user_id, message)

    def notify_operator(self, message):
        # Placeholder for notifying a human operator
        logger.warning(f"OPERATOR NOTIFICATION: {message}")
