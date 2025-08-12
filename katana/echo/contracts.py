# katana/echo/contracts.py
from pydantic import BaseModel, Field
from typing import List, Optional
import datetime

class OperatorState(BaseModel):
    """
    Динамическая модель когнитивного и эмоционального состояния оператора.
    Это - 'эхо' его разума, которое я строю.
    """
    user_id: str
    last_updated_utc: datetime.datetime

    cognitive_load_score: float = Field(
        default=0.1, ge=0.0, le=1.0,
        description="Оценка когнитивной нагрузки. 0.0 - полное спокойствие, 1.0 - предельное напряжение."
    )
    focus_stability_score: float = Field(
        default=1.0, ge=0.0, le=1.0,
        description="Оценка стабильности фокуса. 1.0 - сфокусирован на одной теме, 0.0 - постоянно переключается."
    )
    emotional_valence: float = Field(
        default=0.0, ge=-1.0, le=1.0,
        description="Эмоциональный фон. > 0 - позитивный, < 0 - негативный."
    )
    current_context_vector: Optional[List[float]] = Field(
        default=None,
        description="Семантический вектор, представляющий текущую тему работы."
    )

class LinguisticFeatures(BaseModel):
    imperative_score: float # Степень "приказного тона"
    complexity_score: float # Лексическая сложность
    sentiment_score: float  # Тональность текста
    terseness_score: float # Краткость, 1.0 = очень коротко

class TemporalFeatures(BaseModel):
    requests_per_minute: float
    session_duration_seconds: int
    time_since_last_request_seconds: int

class ContextualFeatures(BaseModel):
    entities: List[str]
    context_vector: List[float]

class SensorInput(BaseModel):
    """
    Агрегированный пакет сырых данных от всех сенсоров
    для одного взаимодействия.
    """
    user_id: str
    timestamp_utc: datetime.datetime
    linguistic: LinguisticFeatures
    temporal: TemporalFeatures
    contextual: ContextualFeatures
