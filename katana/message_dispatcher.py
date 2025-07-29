import logging
from katana.agent_router.router import AgentRouter

logger = logging.getLogger(__name__)


class MessageDispatcher:
    def __init__(self, router: AgentRouter):
        self.router = router

    async def dispatch(self, source, user_id, message):
        logger.info(f"Dispatching message from {source} for user {user_id}")
        request = {"user_id": user_id, "message": message}
        return await self.router.route_request(request)
