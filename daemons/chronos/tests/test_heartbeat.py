import asyncio
import pytest
import nats

@pytest.mark.asyncio
async def test_chronos_heartbeat():
    """
    Tests that the Chronos daemon is publishing heartbeats to NATS.
    This is an integration test and requires the NATS server to be running.
    """
    nc = await nats.connect("nats://localhost:4222")

    sub = await nc.subscribe("chronos.tick.1s")

    try:
        # Wait for a message for up to 5 seconds.
        msg = await sub.next_msg(timeout=5)
        assert msg is not None
        # You could also assert the content of the message if needed, e.g.,
        # assert float(msg.data.decode()) > 0
    except asyncio.TimeoutError:
        pytest.fail("Did not receive a heartbeat message within 5 seconds.")
    finally:
        await sub.unsubscribe()
        await nc.close()
