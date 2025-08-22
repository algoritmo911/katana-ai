# =======================================================================================================================
# ID ПРОТОКОЛА: Polis-v1.0-TheDigitalCivilization
# КОМПОНЕНТ: The Aether
# ОПИСАНИЕ: Сетевой P2P-слой, основанный на libp2p. Обеспечивает обнаружение,
# соединение и общение между агентами.
# =======================================================================================================================

import asyncio
import json
from libp2p import new_host
from libp2p.peer.peerinfo import PeerInfo
from libp2p.typing import TProtocol
from libp2p.pubsub import Gossipsub

# A placeholder for a protocol ID for our specific application
DIRECT_MESSAGE_PROTOCOL_ID = TProtocol("/katana/polis/direct/1.0.0")
DISCOVERY_TOPIC = "/katana/polis/discovery/1.0.0"

class Aether:
    """
    The Aether module encapsulates the libp2p networking logic for an agent.
    """
    def __init__(self):
        self.host = None
        self.gossipsub = None
        # A queue for all structured messages received (direct and broadcast)
        self.message_queue = asyncio.Queue()

    async def start(self):
        """
        Initializes and starts the libp2p host, making it listen for connections.
        """
        # Create a gossipsub router
        self.gossipsub = Gossipsub(protocols_for_discovery=[DIRECT_MESSAGE_PROTOCOL_ID])

        # Create a new libp2p host
        self.host = await new_host(pubsub=self.gossipsub)

        # Set a stream handler for direct messages
        self.host.set_stream_handler(DIRECT_MESSAGE_PROTOCOL_ID, self._direct_stream_handler)

        # Start listening on a random TCP port
        listen_addr = "/ip4/0.0.0.0/tcp/0"
        await self.host.get_network().listen(listen_addr)

        # Subscribe to the discovery topic
        await self.gossipsub.subscribe(DISCOVERY_TOPIC)
        # Add a listener for broadcast messages
        self.gossipsub.add_listener(DISCOVERY_TOPIC, self._broadcast_message_handler)

        print(f"[{self.host.get_id().to_string()[:8]}] Aether node started.")
        print("Listening on:")
        for addr in self.host.get_addrs():
            print(f"- {addr}")

        return self.host

    async def broadcast_message(self, message_dict: dict):
        """Broadcasts a message to all peers on the discovery topic."""
        message_json = json.dumps(message_dict)
        await self.gossipsub.publish(DISCOVERY_TOPIC, message_json.encode('utf-8'))

    async def send_direct_message(self, peer_id_str: str, message_dict: dict):
        """Sends a direct, one-way message to a specific peer."""
        if not self.host:
            raise RuntimeError("Host not started.")

        peer_id = self.host.get_peerstore().peer_id_from_string(peer_id_str)

        try:
            stream = await self.host.new_stream(peer_id, [DIRECT_MESSAGE_PROTOCOL_ID])
            message_json = json.dumps(message_dict)
            await stream.write(message_json.encode('utf-8'))
            await stream.close()
            print(f"[{self.host.get_id().to_string()[:8]}] Sent direct message to {peer_id_str[:8]}")
        except Exception as e:
            print(f"Failed to send direct message to {peer_id_str[:8]}: {e}")

    def _broadcast_message_handler(self, msg):
        """Internal handler for broadcast messages."""
        try:
            # Ignore messages from self
            if msg.from_id == self.host.get_id():
                return

            message_dict = json.loads(msg.data.decode('utf-8'))
            # Add sender info to the message for processing
            message_dict['__sender_id'] = msg.from_id.to_string()
            print(f"\n[{self.host.get_id().to_string()[:8]}] Received broadcast: {message_dict}")
            self.message_queue.put_nowait(message_dict)
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass # Ignore malformed messages

    async def _direct_stream_handler(self, stream):
        """Internal handler for direct messages."""
        try:
            data = await stream.read()
            message_dict = json.loads(data.decode('utf-8'))
            # Add sender info
            message_dict['__sender_id'] = stream.get_remote_peer().to_string()
            print(f"\n[{self.host.get_id().to_string()[:8]}] Received direct message: {message_dict}")
            await self.message_queue.put(message_dict)
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
        finally:
            await stream.close()


async def main():
    """
    A simple test function to demonstrate broadcast and direct messaging.
    """
    node1 = Aether()
    node2 = Aether()
    host1 = await node1.start()
    host2 = await node2.start()

    # Give nodes a moment to discover each other via gossipsub
    await asyncio.sleep(1)

    # To connect them directly for this test
    await host1.connect(PeerInfo.from_string(f"{host2.get_addrs()[0]}/p2p/{host2.get_id()}"))

    # 1. Node 1 broadcasts a "seeking" message
    print("\n--- Test: Node 1 broadcasting ---")
    await node1.broadcast_message({"type": "seeking", "id": "node1"})

    # 2. Node 2 should receive it
    try:
        received_broadcast = await asyncio.wait_for(node2.message_queue.get(), timeout=5.0)
        assert received_broadcast["type"] == "seeking"
        assert received_broadcast["id"] == "node1"
        sender_id = received_broadcast["__sender_id"]
        print("--- Test Passed: Node 2 received broadcast. ---")

        # 3. Node 2 sends a direct reply
        print("\n--- Test: Node 2 sending direct reply ---")
        await node2.send_direct_message(sender_id, {"type": "ack", "id": "node2"})

        # 4. Node 1 should receive it
        received_direct = await asyncio.wait_for(node1.message_queue.get(), timeout=5.0)
        assert received_direct["type"] == "ack"
        assert received_direct["id"] == "node2"
        print("--- Test Passed: Node 1 received direct reply. ---")

    except asyncio.TimeoutError:
        print("--- Test Failed: Did not receive message in time. ---")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
