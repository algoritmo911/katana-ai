"""
Модуль определяет AI-агента "Юрист-Интерпретатор" (`IntentParser`).

Его задача — преобразовать запрос на естественном языке в формализованный
"Контракт Намерений" (`IntentContract`).
"""

import json
from typing import Dict, Any, Optional

from katana.contracts.intent_contract import IntentContract, Constraints

class IntentParser:
    """
    AI-агент, который парсит естественный язык в `IntentContract`.
    """

    def __init__(self):
        """
        Инициализация парсера. В будущем здесь может быть конфигурация
        для подключения к LLM.
        """
        pass

    def _mock_llm_call(self, query: str) -> Dict[str, Any]:
        """
        Имитирует вызов LLM с жестко заданной JSON-схемой.

        На данном этапе это mock с несколькими правилами, который реагирует
        на ключевые слова. В реальной системе здесь будет вызов внешней модели.
        """
        # Сценарий 1: Полный, хорошо определенный запрос
        if "повысить удержание пользователей на 10%" in query and \
           "следующем квартале" in query:

            return {
                "objective": "Повысить удержание пользователей на 10%",
                "timeframe": "Следующий квартал",
                "key_results": [
                    "Удержание пользователей достигло значения X+10%",
                    "Отток пользователей снизился на Y%"
                ],
                "constraints": {
                    "max_budget": 50000,
                    "currency": "SC",
                    "forbidden_methods": ["темные паттерны"]
                }
            }

        # Сценарий 2: Неполный запрос (отсутствуют сроки, бюджет и т.д.)
        elif "повысить удержание пользователей" in query:
            return {
                "objective": "Повысить удержание пользователей",
                "timeframe": None,
                "key_results": [],
                "constraints": {}
            }

        # Сценарий 3: Нераспознанный запрос
        else:
            raise ValueError("Не удалось распознать намерение в запросе.")


    def parse(self, query: str) -> IntentContract:
        """
        Парсит запрос и возвращает валидный `IntentContract`.

        Args:
            query: Запрос на естественном языке.

        Returns:
            Экземпляр `IntentContract`.

        Raises:
            ValueError: Если не удалось создать валидный контракт.
            pydantic.ValidationError: Если данные от LLM не соответствуют схеме.
        """
        try:
            structured_data = self._mock_llm_call(query)
        except ValueError as e:
            raise e

        contract = IntentContract(**structured_data)

        return contract
