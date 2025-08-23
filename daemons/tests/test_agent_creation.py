import asyncio
import httpx
import pytest
from neo4j import GraphDatabase

# --- Test Configuration ---
ORCHESTRATOR_URL = "http://localhost:8000"
NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "password")

# Sample Agent Definition based on the DSL
SAMPLE_AGENT = {
    "apiVersion": "prometheus.katana.ai/v1alpha1",
    "kind": "AutonomousTradingAgent",
    "metadata": {
        "name": "test-agent-001",
        "labels": {
            "strategy": "ma-crossover",
            "risk": "medium"
        }
    },
    "spec": {
        "description": "A simple moving average crossover agent.",
        "state": {
            "isHoldingPosition": {
                "type": "bool",
                "initialValue": False
            }
        },
        "sources": [
            {
                "name": "btc_1m",
                "type": "chronos.klines",
                "parameters": {
                    "product_id": "BTC-USD",
                    "granularity": "ONE_MINUTE"
                }
            }
        ],
        "triggers": [
            {
                "on": "source.btc_1m.updated",
                "name": "on_new_candle",
                "evaluates": "main_logic"
            }
        ],
        "strategy": {
            "main_logic": {
                "steps": [
                    {
                        "condition": {
                            "type": "temporal.crossover",
                            "inputs": {
                                "series_a": "SMA(source.btc_1m.close, 10)",
                                "series_b": "SMA(source.btc_1m.close, 30)"
                            }
                        }
                    }
                ]
            }
        }
    }
}


@pytest.mark.asyncio
async def test_agent_conception_to_knowledge_graph():
    """
    Tests the full end-to-end flow of agent creation:
    1. POSTing a definition to the Orchestrator.
    2. Orchestrator publishing a NATS event.
    3. Mnemosyne consuming the event and creating a node in Neo4j.

    This is an integration test and requires the full stack to be running.
    """
    neo4j_driver = None
    agent_name = SAMPLE_AGENT["metadata"]["name"]

    try:
        # --- Step 1: Clean up any previous test data ---
        neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
        with neo4j_driver.session() as session:
            session.run("MATCH (a:Agent {name: $name}) DETACH DELETE a", name=agent_name)

        # --- Step 2: Send the agent definition to the Orchestrator ---
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{ORCHESTRATOR_URL}/agents", json=SAMPLE_AGENT)
            assert response.status_code == 201, f"Failed to create agent: {response.text}"
            assert response.json() == {"message": f"Agent '{agent_name}' conceived successfully."}

        # --- Step 3: Wait for event propagation ---
        await asyncio.sleep(3) # Allow time for NATS message and DB write

        # --- Step 4: Verify the agent node was created in Neo4j ---
        with neo4j_driver.session() as session:
            result = session.run("MATCH (a:Agent {name: $name}) RETURN a", name=agent_name)
            record = result.single()

            assert record is not None, f"Agent node '{agent_name}' not found in Neo4j."

            agent_node = record["a"]
            assert agent_node["name"] == agent_name
            assert agent_node["kind"] == SAMPLE_AGENT["kind"]
            # Labels are stored as a string representation of a dict
            assert agent_node["labels"] == str(SAMPLE_AGENT["metadata"]["labels"])

    finally:
        # --- Step 5: Clean up ---
        if neo4j_driver:
            with neo4j_driver.session() as session:
                session.run("MATCH (a:Agent {name: $name}) DETACH DELETE a", name=agent_name)
            neo4j_driver.close()
