# katana/morpheus/contracts.py
from pydantic import BaseModel, Field
from typing import List, Literal, Dict, Any

class CodeDebtFinding(BaseModel):
    type: Literal["code_debt"] = "code_debt"
    file_path: str
    line_number: int
    cyclomatic_complexity: int
    details: str

class PerformanceRegressionFinding(BaseModel):
    type: Literal["performance_regression"] = "performance_regression"
    endpoint_or_function: str
    latency_increase_ms: float
    baseline_ms: float
    current_ms: float

class KnowledgeIntegrityFinding(BaseModel):
    type: Literal["knowledge_integrity"] = "knowledge_integrity"
    issue_type: Literal["orphan_concept", "contradiction"]
    concept_id: str
    details: str

class ConceptualHotspotFinding(BaseModel):
    type: Literal["conceptual_hotspot"] = "conceptual_hotspot"
    concept_name: str
    stress_level: float = Field(..., ge=0.0, le=1.0)
    contributing_factors: List[str]

class DiagnosticReport(BaseModel):
    """
    Единый структурированный отчет, который является результатом
    фазы самодиагностики ('Анализатор Снов').
    """
    report_id: str
    timestamp_utc: str
    findings: List[
        CodeDebtFinding |
        PerformanceRegressionFinding |
        KnowledgeIntegrityFinding |
        ConceptualHotspotFinding
    ]
