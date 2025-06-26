# katana-ai/core/bridge/sc_link.py

import httpx
from loguru import logger

SC_API_BASE = "http://localhost:8000/api"

class SCLink:
    def __init__(self):
        self.base_url = SC_API_BASE

    def ping(self) -> bool:
        """Проверяет доступность ядра SC"""
        try:
            r = httpx.get(f"{self.base_url}/status")
            return r.status_code == 200
        except Exception as e:
            logger.error(f"[SCLink] Ping failed: {e}")
            return False

    def submit_knowledge_unit(self, ku: dict) -> bool:
        """Отправка KU в SC"""
        try:
            r = httpx.post(f"{self.base_url}/knowledge/units", json=ku)
            return r.status_code == 200
        except Exception as e:
            logger.error(f"[SCLink] KU submission failed: {e}")
            return False

    def repair_graph(self) -> str:
        """Запуск восстановления графа знаний"""
        try:
            r = httpx.post(f"{self.base_url}/graph/repair")
            return r.text
        except Exception as e:
            logger.error(f"[SCLink] Graph repair failed: {e}")
            return "ERROR"
