"""
Модуль определяет структуру данных для "Контракта Намерений".

Этот контракт является формализованным, машинно-читаемым представлением
стратегической цели, полученной из запроса на естественном языке.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

class Constraints(BaseModel):
    """
    Определяет ограничения и рамки для выполнения цели.
    """
    max_budget: Optional[int] = Field(
        None,
        description="Максимальный бюджет, выделенный на достижение цели."
    )
    currency: Optional[str] = Field(
        "SC",
        description="Валюта бюджета (по умолчанию 'SC' - Strategic Credits)."
    )
    forbidden_methods: List[str] = Field(
        default_factory=list,
        description="Список запрещенных методов или подходов."
    )

class IntentContract(BaseModel):
    """
    Контракт Намерений.

    Формализует стратегическую цель, ее временные рамки, ключевые результаты
    и наложенные ограничения.
    """
    objective: str = Field(
        ...,
        description="Четко сформулированная, измеримая цель."
    )
    timeframe: Optional[str] = Field(
        None,
        description="Период времени, за который цель должна быть достигнута."
    )
    key_results: List[str] = Field(
        default_factory=list,
        description="Список ключевых результатов для отслеживания прогресса."
    )
    constraints: Constraints = Field(
        default_factory=Constraints,
        description="Ограничения, которые необходимо соблюдать."
    )
