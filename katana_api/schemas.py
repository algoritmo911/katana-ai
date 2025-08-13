from pydantic import BaseModel, Field
from typing import List, Optional

# --- Error Schemas ---

class ErrorDetailSchema(BaseModel):
    """
    Schema for the nested 'error' object in a standardized error response.
    """
    code: str = Field(..., description="A unique, machine-readable error code.", example="invalid_token")
    message: str = Field(..., description="A human-readable message explaining the error.", example="Invalid authentication credentials.")

class ErrorResponseSchema(BaseModel):
    """
    Schema for a standardized JSON error response.
    """
    error: ErrorDetailSchema


# --- Orchestrator Schemas ---

class RoundResultSummarySchema(BaseModel):
    """
    Schema for the summary of a single task result within a round.
    """
    task: str
    success: bool
    details: str

class RoundMetricSchema(BaseModel):
    """
    Schema for the metrics of a single orchestrator round.
    """
    timestamp: str
    batch_size_at_round_start: int
    tasks_processed_count: int
    successful_tasks_count: int
    failed_tasks_count: int
    success_rate: float
    time_taken_seconds: float
    batch_tasks_content: List[str]
    results_summary: List[RoundResultSummarySchema]

class StatusResponseSchema(BaseModel):
    """
    Schema for the response of the /orchestrator/status endpoint.
    """
    current_batch_size: int
    task_queue_length: int
    total_metrics_rounds: int
    last_10_rounds_metrics: List[RoundMetricSchema]

# --- Health Schemas ---
class HealthResponseSchema(BaseModel):
    """
    Schema for the response of the /health endpoint.
    """
    status: str = "ok"
