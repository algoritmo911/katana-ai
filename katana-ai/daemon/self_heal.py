# katana-ai/daemon/self_heal.py

from core.bridge.sc_link import SCLink
from loguru import logger
import time

sc = SCLink()

def run_self_heal_loop():
    logger.info("[SelfHeal] Init self-healing loop for SC")
    while True:
        is_online = sc.ping()
        if not is_online:
            logger.warning("[SelfHeal] SC offline detected. Initiating auto-repair.")
            result = sc.repair_graph()
            logger.info(f"[SelfHeal] Repair result: {result}")
        else:
            logger.debug("[SelfHeal] SC status OK.")
        time.sleep(60)  # Проверять каждую минуту
