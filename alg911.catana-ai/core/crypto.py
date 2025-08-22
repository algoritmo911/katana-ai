# =======================================================================================================================
# ID ПРОТОКОЛА: Polis-v1.0-TheDigitalCivilization
# КОМПОНЕНТ: Crypto
# ОПИСАНИЕ: Модуль для криптографических операций: генерация ключей,
# подпись сообщений и верификация подписей.
# =======================================================================================================================

from Crypto.PublicKey import Ed25519
from Crypto.Hash import SHA256
from Crypto.Signature import eddsa
import os

# Define a directory to store keys, relative to this file's location
KEY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agent_keys')

class CryptoManager:
    """
    Handles cryptographic operations for an agent, including key generation,
    loading, signing, and verification using the Ed25519 algorithm.
    """
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.key_path = os.path.join(KEY_DIR, f"{self.agent_id}_key.pem")
        self.public_key_path = os.path.join(KEY_DIR, f"{self.agent_id}_key.pub")
        self.private_key = None
        self.public_key = None
        self._load_or_generate_keys()

    def _load_or_generate_keys(self):
        """
        Loads existing keys for the agent, or generates and saves a new
        key pair if they don't exist.
        """
        os.makedirs(KEY_DIR, exist_ok=True)
        if os.path.exists(self.key_path):
            # Load existing private key
            with open(self.key_path, 'rb') as f:
                self.private_key = Ed25519.import_key(f.read())
            # Load existing public key
            with open(self.public_key_path, 'rb') as f:
                self.public_key = Ed25519.import_key(f.read())
            print(f"Crypto: Loaded existing keys for agent {self.agent_id}")
        else:
            # Generate new keys
            self.private_key = Ed25519.generate()
            self.public_key = self.private_key.publickey()
            # Save the private key
            with open(self.key_path, 'wb') as f:
                f.write(self.private_key.export_key(format='PEM'))
            # Save the public key
            with open(self.public_key_path, 'wb') as f:
                f.write(self.public_key.export_key(format='PEM'))
            print(f"Crypto: Generated and saved new keys for agent {self.agent_id}")

    def sign_message(self, message: str) -> bytes:
        """
        Signs a message with the agent's private key.

        :param message: The string message to sign.
        :return: The signature as bytes.
        """
        h = SHA256.new(message.encode('utf-8'))
        signer = eddsa.new(self.private_key, 'rfc8032')
        signature = signer.sign(h)
        return signature

    @staticmethod
    def verify_signature(public_key_pem: bytes, message: str, signature: bytes) -> bool:
        """
        Verifies a signature with a given public key.

        :param public_key_pem: The PEM-encoded public key of the signer.
        :param message: The original string message.
        :param signature: The signature to verify.
        :return: True if the signature is valid, False otherwise.
        """
        try:
            public_key = Ed25519.import_key(public_key_pem)
            h = SHA256.new(message.encode('utf-8'))
            verifier = eddsa.new(public_key, 'rfc8032')
            verifier.verify(h, signature)
            return True
        except (ValueError, TypeError):
            return False

if __name__ == '__main__':
    # --- Test ---
    print("--- CryptoManager Test ---")

    # 1. Create two crypto managers for two agents
    agent1_crypto = CryptoManager(agent_id="agent-test-1")
    agent2_crypto = CryptoManager(agent_id="agent-test-2")

    # 2. Agent 1 signs a message
    msg_to_sign = "Protocol Polis: The First Word"
    signature = agent1_crypto.sign_message(msg_to_sign)
    print(f"Agent 1 signed message: '{msg_to_sign}'")

    # 3. Agent 2 verifies the signature using Agent 1's public key
    agent1_public_key_pem = agent1_crypto.public_key.export_key(format='PEM')

    # Test with the correct key and message
    is_valid = CryptoManager.verify_signature(agent1_public_key_pem, msg_to_sign, signature)
    print(f"Agent 2 verifying with correct key and message... Valid: {is_valid}")
    assert is_valid

    # Test with the wrong message
    is_valid_wrong_msg = CryptoManager.verify_signature(agent1_public_key_pem, "some other message", signature)
    print(f"Agent 2 verifying with wrong message... Valid: {is_valid_wrong_msg}")
    assert not is_valid_wrong_msg

    # Test with the wrong key (Agent 2's public key)
    agent2_public_key_pem = agent2_crypto.public_key.export_key(format='PEM')
    is_valid_wrong_key = CryptoManager.verify_signature(agent2_public_key_pem, msg_to_sign, signature)
    print(f"Agent 2 verifying with wrong public key... Valid: {is_valid_wrong_key}")
    assert not is_valid_wrong_key

    # Clean up test key files
    os.remove(agent1_crypto.key_path)
    os.remove(agent1_crypto.public_key_path)
    os.remove(agent2_crypto.key_path)
    os.remove(agent2_crypto.public_key_path)
    print("\nCleaned up test key files.")

    print("\n--- CryptoManager Verified ---")
