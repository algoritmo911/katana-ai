import asyncio
import json
import logging
import nats
from neo4j import AsyncGraphDatabase, exceptions

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Neo4j Driver Setup ---
NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "password")
neo4j_driver = None

async def get_neo4j_driver():
    """Initializes and returns the async Neo4j driver."""
    global neo4j_driver
    if neo4j_driver is None:
        try:
            neo4j_driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
            await neo4j_driver.verify_connectivity()
            logger.info("Connected to Neo4j database.")
        except exceptions.ServiceUnavailable as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            neo4j_driver = None
    return neo4j_driver

async def close_neo4j_driver():
    """Closes the Neo4j driver connection."""
    global neo4j_driver
    if neo4j_driver:
        await neo4j_driver.close()
        logger.info("Disconnected from Neo4j database.")

# --- NATS Message Handler ---
async def agent_created_handler(msg):
    """
    Handles 'agent.created' events by creating a node in the knowledge graph.
    """
    subject = msg.subject
    data = json.loads(msg.data.decode())
    agent_name = data.get("metadata", {}).get("name")

    if not agent_name:
        logger.error(f"Received malformed agent creation event on '{subject}': missing name.")
        return

    logger.info(f"Received agent creation event for '{agent_name}' on subject '{subject}'.")

    driver = await get_neo4j_driver()
    if not driver:
        logger.error("Cannot process event: Neo4j driver not available.")
        return

    try:
        async with driver.session() as session:
            # Using MERGE to prevent creating duplicate agents on replay
            await session.run(
                """
                MERGE (a:Agent {name: $name})
                ON CREATE SET a.labels = $labels, a.apiVersion = $apiVersion, a.kind = $kind
                """,
                name=agent_name,
                labels=str(data.get("metadata", {}).get("labels", {})), # Storing labels as string
                apiVersion=data.get("apiVersion"),
                kind=data.get("kind")
            )
        logger.info(f"Successfully created or merged node for agent '{agent_name}' in the knowledge graph.")
    except Exception as e:
        logger.error(f"Failed to create node for agent '{agent_name}': {e}")

# --- Main Daemon Logic ---
async def main():
    """
    The main function for the Mnemosyne daemon.
    Connects to NATS and Neo4j and processes events.
    """
    await get_neo4j_driver() # Initial connection attempt

    nc = None
    try:
        nc = await nats.connect("nats://localhost:4222", error_cb=lambda e: logger.error(f"NATS Error: {e}"))
        logger.info("Connected to NATS.")

        # Subscribe to agent creation events
        await nc.subscribe("prometheus.events.agent.created", cb=agent_created_handler)
        logger.info("Subscribed to 'prometheus.events.agent.created' subject.")

        # Keep the daemon running
        while True:
            await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"An unexpected error occurred in Mnemosyne main loop: {e}")
    finally:
        if nc and not nc.is_closed:
            await nc.close()
        await close_neo4j_driver()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Mnemosyne daemon stopped.")
