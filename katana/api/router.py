from fastapi import APIRouter, Depends, Security, HTTPException
from fastapi.security.api_key import APIKeyHeader
from typing import Dict, Any

from katana.agent_router.registry import AgentRegistry
from katana.agent_router.router import AgentRouter
from katana.agent_router.dispatcher import RoundRobinDispatcher
from katana.agent_router.communication import CommunicationLayer

router = APIRouter()

# For simplicity, we create a single instance of the registry and router.
# In a real application, you might use a dependency injection system.
agent_registry = AgentRegistry()
dispatcher = RoundRobinDispatcher(agent_registry)
communication_layer = CommunicationLayer()
agent_router = AgentRouter(agent_registry, dispatcher, communication_layer)


def get_agent_router():
    return agent_router


def get_agent_registry():
    return agent_registry


@router.post("/route")
async def route_request(
    request: Dict[str, Any],
    router: AgentRouter = Depends(get_agent_router),
):
    return await router.route_request(request)


@router.get("/agents")
async def list_agents(
    registry: AgentRegistry = Depends(get_agent_registry),
):
    return registry.list_agents()


API_KEY = "your-secret-api-key"  # In a real app, load this from a secure source
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == API_KEY:
        return api_key
    else:
        raise HTTPException(status_code=403, detail="Could not validate credentials")


@router.post("/agents/register")
async def register_agent(
    agent_id: str,
    agent_info: Dict[str, Any],
    registry: AgentRegistry = Depends(get_agent_registry),
    api_key: str = Depends(get_api_key),
):
    registry.register_agent(agent_id, agent_info)
    return {"status": "ok", "agent_id": agent_id}


@router.post("/agents/deregister")
async def deregister_agent(
    agent_id: str,
    registry: AgentRegistry = Depends(get_agent_registry),
    api_key: str = Depends(get_api_key),
):
    registry.deregister_agent(agent_id)
    return {"status": "ok", "agent_id": agent_id}
