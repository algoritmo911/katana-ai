from fastapi import APIRouter, Request, Depends
from typing import Any, Dict

from .schemas import StatusResponseSchema, HealthResponseSchema
from .security import get_current_token

router = APIRouter(
    prefix="/api/v1",
)

@router.get("/health",
            response_model=HealthResponseSchema,
            tags=["Health"],
            summary="Check API Health"
            )
async def health_check():
    """
    Endpoint to verify that the API is running.
    This endpoint is not protected by authentication.
    """
    return {"status": "ok"}

@router.get("/orchestrator/status",
            response_model=StatusResponseSchema,
            tags=["Orchestrator"],
            summary="Get Orchestrator Status",
            dependencies=[Depends(get_current_token)])
async def get_orchestrator_status(request: Request) -> Dict[str, Any]:
    """
    Provides the current status of the TaskOrchestrator,
    including current batch size, task queue length, and metrics for the last 10 rounds.
    """
    orchestrator = request.app.state.orchestrator
    if orchestrator is None:
        # This case should ideally not happen due to the lifespan manager
        return {"error": "Orchestrator not initialized"}
    return orchestrator.get_status()

# We will add more endpoints here in the future.
