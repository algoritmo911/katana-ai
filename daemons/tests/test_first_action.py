import pytest
import json
import asyncio
import httpx
from neo4j import GraphDatabase

# --- Test Configuration ---
ORCHESTRATOR_URL = "http://localhost:8000"
NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "password")
NATS_URL = "nats://localhost:4222"

# Agent definition from the Phase 3 Spec
IMPULSE_BUYER_AGENT = {
    "apiVersion": "prometheus.katana.ai/v1alpha1",
    "kind": "AutonomousTradingAgent",
    "metadata": {
        "name": "impulse-buyer-agent-001"
    },
    "spec": {
        "state": {
            "isHoldingPosition": {"type": "bool", "initialValue": False}
        },
        "sources": [],
        "triggers": [
            {
                "on": "chronos.tick.1s",
                "name": "on_every_second",
                "evaluates": "buy_on_tick_logic"
            }
        ],
        "strategy": {
            "buy_on_tick_logic": {
                "steps": [
                    {"condition": {"type": "state.is_false", "input": "state.isHoldingPosition"}},
                    {
                        "actions": [
                            {
                                "type": "hephaestus.trade",
                                "parameters": {
                                    "action": "BUY",
                                    "product_id": "BTC-USD",
                                    "amount": "0.001"
                                }
                            },
                            {
                                "type": "state.set",
                                "parameters": {
                                    "variable": "isHoldingPosition",
                                    "value": True
                                }
                            }
                        ]
                    }
                ]
            }
        }
    }
}

# This test is a full end-to-end test and requires all daemons and infrastructure
# to be running. It follows the "local verification" protocol.
@pytest.mark.asyncio
async def test_first_thought_and_action():
    """
    Verifies the full cycle: conception -> trigger -> logic -> action -> result -> memory.
    """
    # For this test, we assume the daemons are running. We will interact with them.
    # We will need a NATS client to inject the trigger and listen for results.
    import nats
    nats_client = await nats.connect(NATS_URL)
    neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    agent_name = IMPULSE_BUYER_AGENT["metadata"]["name"]

    try:
        # --- Step 0: Cleanup from previous runs ---
        with neo4j_driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

        # --- Step 1 & 2: Conceive the Agent ---
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(f"{ORCHESTRATOR_URL}/agents", json=IMPULSE_BUYER_AGENT)
            assert response.status_code == 201

        # --- Step 3: Verify Agent creation in Memory (Mnemosyne) ---
        await asyncio.sleep(1) # Allow Mnemosyne to process the event
        with neo4j_driver.session() as session:
            result = session.run("MATCH (a:Agent {name: $name}) RETURN a", name=agent_name)
            assert result.single() is not None, "Agent node was not created in Neo4j"

        # --- Step 4, 5, 6, 7, 8: Trigger the agent and listen for its action ---
        action_future = asyncio.Future()
        async def action_listener(msg):
            action_future.set_result(json.loads(msg.data.decode()))

        action_subject = f"agent.{agent_name}.action.execute"
        await nats_client.subscribe(action_subject, cb=action_listener)

        # Publish the trigger event
        await nats_client.publish("chronos.tick.1s", b'tick')

        # Wait for the agent to publish its action command
        action_command = await asyncio.wait_for(action_future, timeout=5)

        assert action_command["type"] == "hephaestus.trade"
        assert action_command["parameters"]["product_id"] == "BTC-USD"

        # --- Step 9 & 10: Simulate Hephaestus's response ---
        # In a real test, Hephaestus would be running. Here, we simulate its part.
        result_subject = f"agent.{agent_name}.action.result"
        result_payload = {"status": "SUCCESS", "details": {"order_id": "sim-order-123"}}
        await nats_client.publish(result_subject, json.dumps(result_payload).encode())

        # --- Step 11, 12, 13: Verify state change and memory ---
        # This part is harder to test without direct access to the agent's state.
        # We will verify it by triggering the agent again and ensuring it does NOT act.

        second_action_future = asyncio.Future()
        # Resubscribe to be sure
        await nats_client.subscribe(action_subject, cb=lambda msg: second_action_future.set_result(True))

        # Publish a second trigger
        await nats_client.publish("chronos.tick.1s", b'tick2')

        try:
            # We expect this to time out, as the agent's state should prevent a second action
            await asyncio.wait_for(second_action_future, timeout=2)
            pytest.fail("Agent acted a second time when its state should have prevented it.")
        except asyncio.TimeoutError:
            # This is the expected outcome!
            pass

        # Optional: Verify the full graph in Neo4j (complex query)

    finally:
        # --- Final Cleanup ---
        if nats_client:
            await nats_client.close()
        if neo4j_driver:
            with neo4j_driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
            neo4j_driver.close()
