import uvicorn
import logging
import nats
from fastapi import FastAPI, HTTPException
from typing import Dict

from daemons.orchestrator.dsl import AgentDefinition

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory storage for agents and NATS client
agents: Dict[str, AgentDefinition] = {}
nats_client = None

# --- FastAPI App Setup ---
app = FastAPI(
    title="Prometheus Orchestrator",
    description="The brain and will of the system.",
    version="0.1-alpha",
)

@app.on_event("startup")
async def startup_event():
    """Connect to NATS on application startup."""
    global nats_client
    try:
        nats_client = await nats.connect("nats://localhost:4222")
        logger.info("Connected to NATS server.")
    except Exception as e:
        logger.error(f"Failed to connect to NATS: {e}")
        nats_client = None # Ensure client is None if connection fails

@app.on_event("shutdown")
async def shutdown_event():
    """Disconnect from NATS on application shutdown."""
    if nats_client:
        await nats_client.close()
        logger.info("Disconnected from NATS server.")

@app.get("/health", tags=["Monitoring"])
async def health_check():
    """Checks if the orchestrator is running."""
    return {"status": "ok", "nats_connected": nats_client.is_connected if nats_client else False}

@app.post("/agents", status_code=201, tags=["Agents"])
async def conceive_agent(agent_def: AgentDefinition):
    """
    Receives an agent definition, validates it, and brings the agent into existence.
    """
    agent_name = agent_def.metadata.name
    if agent_name in agents:
        raise HTTPException(status_code=409, detail=f"Agent '{agent_name}' already exists.")

    # Store the agent definition
    agents[agent_name] = agent_def

    # Log the conception
    logger.info(f"Agent '{agent_name}' has been conceived.")

    # Publish the creation event to NATS
    if nats_client and nats_client.is_connected:
        event_subject = "prometheus.events.agent.created"
        event_payload = agent_def.model_dump_json().encode()
        await nats_client.publish(event_subject, event_payload)
        logger.info(f"Published creation event for agent '{agent_name}' to subject '{event_subject}'.")
    else:
        logger.error("Cannot publish agent creation event: NATS client not connected.")
        # Depending on requirements, we might want to raise an error here
        raise HTTPException(status_code=503, detail="NATS service is unavailable.")

    return {"message": f"Agent '{agent_name}' conceived successfully."}

if __name__ == "__main__":
    # For development, run this from the root directory using:
    # uvicorn daemons.orchestrator.main:app --reload
    # The main block below is for a simple, non-reloading execution.
    uvicorn.run(app, host="0.0.0.0", port=8000)
