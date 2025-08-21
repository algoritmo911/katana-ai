import redis
import json
import threading
import time
import logging

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SystemState:
    """
    Manages the System State Vector (SSV) and broadcasts it to Redis.
    """
    def __init__(self, redis_host='localhost', redis_port=6379, broadcast_channel='system_state_vector'):
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, db=0)
        self.broadcast_channel = broadcast_channel
        self.ssv = {
            'fatigue': 0.0,
            'performance_degradation': 0.0,
            'api_latency': {},
            'active_goal': 'none',
            'command_frequency': {},
            'error_rate': 0.0,
        }
        self.lock = threading.Lock()
        self.broadcast_thread = threading.Thread(target=self._broadcast_ssv, daemon=True)
        self.broadcast_thread.start()

    def update_ssv(self, key, value):
        """
        Updates a specific key in the SSV.
        """
        with self.lock:
            self.ssv[key] = value
            logging.info(f"SSV updated: {key} = {value}")

    def get_ssv(self):
        """
        Returns the current SSV.
        """
        with self.lock:
            return self.ssv.copy()

    def _broadcast_ssv(self):
        """
        Periodically broadcasts the SSV to the specified Redis channel.
        """
        while True:
            ssv_json = json.dumps(self.get_ssv())
            self.redis_client.publish(self.broadcast_channel, ssv_json)
            logging.info(f"Broadcasted SSV to {self.broadcast_channel}")
            time.sleep(5)  # Broadcast every 5 seconds

# Global instance of the SystemState
system_state = SystemState()
