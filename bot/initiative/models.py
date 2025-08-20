from pydantic import BaseModel, Field
from typing import List

class ProposedSolution(BaseModel):
    """
    Описывает предлагаемое решение для выявленной проблемы.
    """
    goal: str = Field(..., description="Конкретная, измеримая цель предлагаемого проекта.")
    deliverables: List[str] = Field(..., description="Список ключевых результатов или артефактов.")
    high_level_plan: List[str] = Field(..., description="Разбивка решения на 3-5 высокоуровневых этапов.")

class IntentContract(BaseModel):
    """
    Машиночитаемый контракт, описывающий автономную инициативу.
    Генерируется HypothesisGenerator'ом.
    """
    id: str = Field(..., description="Уникальный идентификатор инициативы, например, INIT-2025-Q3-001.")
    title: str = Field(..., description="Краткое название инициативы (до 10 слов).")
    problem_statement: str = Field(..., description="Прямая цитата или краткое изложение стратегического разрыва.")
    proposed_solution: ProposedSolution
    required_capabilities: List[str] = Field(..., description="Список технологий или навыков, необходимых для реализации.")

class ImpactAnalysis(BaseModel):
    """
    Результаты анализа последствий предлагаемой инициативы.
    """
    affected_modules: List[str]
    estimated_effort: str
    new_dependencies: List[str]
    risks: List[str]

class InitiativeProposal(BaseModel):
    """
    Полное предложение по инициативе, готовое для утверждения.
    """
    status: str
    intent_contract: IntentContract
    impact_analysis: ImpactAnalysis = None
