# =======================================================================================================================
# ID ПРОТОКОЛА: Telos-v1.0-TheSeagullNebula
# КОМПОНЕНТ: Katana Master Control Program (MCP)
# ОПИСАНИЕ: Главный управляющий цикл агента. Запускает мета-когнитивный цикл "Телос"
# для генерации целей, а затем передает их тактическому циклу OODA-P для выполнения.
# =======================================================================================================================

from core.world_modeler import WorldModeler
from core.neurovault import Neurovault
from core.diagnost import Diagnost
from core.cassandra import Cassandra
from core.dream_engine import DreamEngine
from core.action_space import ActionSpace
from core.simulation_matrix import SimulationMatrix
from core.value_judgement_engine import ValueJudgementEngine
import asyncio
import os
import json
import base64
from core.goal_generator import GoalGenerator
from agent_loop import KatanaAgent
from core.aether import Aether
from core.crypto import CryptoManager

async def message_processor_loop(agent_id: str, aether: Aether, crypto: CryptoManager):
    """Handles incoming messages from the aether queue."""
    print(f"[{agent_id}] Starting message processor loop...")
    while True:
        try:
            message = await aether.message_queue.get()
            sender_id = message.get('__sender_id')
            msg_type = message.get('type')

            if msg_type == "SeekingPeers":
                print(f"[{agent_id}] Received SeekingPeers from {sender_id[:8]}")
                # Verify signature
                pub_key_pem = base64.b64decode(message['pub_key_b64'])
                signature = base64.b64decode(message['signature_b64'])
                is_valid = CryptoManager.verify_signature(pub_key_pem, message['original_message'], signature)

                if is_valid:
                    print(f"[{agent_id}] Signature from {sender_id[:8]} is VALID.")
                    # Prepare and send reply
                    reply_msg_str = f"Acknowledged: {sender_id}"
                    reply_sig = crypto.sign_message(reply_msg_str)
                    reply = {
                        "type": "ReadyToCommunicate",
                        "original_message": reply_msg_str,
                        "signature_b64": base64.b64encode(reply_sig).decode('utf-8'),
                        "pub_key_b64": base64.b64encode(crypto.public_key.export_key(format='PEM')).decode('utf-8')
                    }
                    await aether.send_direct_message(sender_id, reply)
                else:
                    print(f"[{agent_id}] Signature from {sender_id[:8]} is INVALID.")

            elif msg_type == "ReadyToCommunicate":
                print(f"[{agent_id}] Received ReadyToCommunicate from {sender_id[:8]}")
                pub_key_pem = base64.b64decode(message['pub_key_b64'])
                signature = base64.b64decode(message['signature_b64'])
                is_valid = CryptoManager.verify_signature(pub_key_pem, message['original_message'], signature)
                if is_valid:
                    print(f"[{agent_id}] ACK signature from {sender_id[:8]} is VALID. First contact established.")
                else:
                    print(f"[{agent_id}] ACK signature from {sender_id[:8]} is INVALID.")

        except Exception as e:
            print(f"[{agent_id}] Error in message loop: {e}")

async def main():
    """
    The main entry point for the fully autonomous Katana agent.
    """
    agent_id = os.environ.get("AGENT_ID", "default_agent")
    print("="*60)
    print(f"KATANA MCP INITIALIZING FOR AGENT: {agent_id}")
    print("="*60)

    # --- Initialize components ---
    crypto = CryptoManager(agent_id=agent_id)
    aether = Aether()

    # --- Start networking and message processing ---
    network_task = asyncio.create_task(aether.start())
    message_loop_task = asyncio.create_task(message_processor_loop(agent_id, aether, crypto))
    await asyncio.sleep(2) # Give network time to start

    # --- Execute First Contact Protocol ---
    print(f"[{agent_id}] Executing 'First Contact' protocol...")
    seeking_msg_str = f"ID: {agent_id}, Protocol: Polis-v1, Status: SeekingPeers"
    signature = crypto.sign_message(seeking_msg_str)

    broadcast_message = {
        "type": "SeekingPeers",
        "original_message": seeking_msg_str,
        "signature_b64": base64.b64encode(signature).decode('utf-8'),
        "pub_key_b64": base64.b64encode(crypto.public_key.export_key(format='PEM')).decode('utf-8')
    }
    await aether.broadcast_message(broadcast_message)
    print(f"[{agent_id}] Broadcasted 'SeekingPeers' message.")

    # In a real app, the loops would run forever. For this test, we wait a bit
    # to allow for the message exchange to happen, then we can exit.
    print(f"[{agent_id}] Waiting for peer interactions... (10s)")
    await asyncio.sleep(10)

    print(f"[{agent_id}] Halting agent.")
    network_task.cancel()
    message_loop_task.cancel()
    try:
        await network_task
        await message_loop_task
    except asyncio.CancelledError:
        print(f"[{agent_id}] All tasks successfully cancelled.")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
