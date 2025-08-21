from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from .auto_healer import AutoHealer, ReflexMap

app = FastAPI(
    title="Katana AutoHealer Service",
    description="Receives anomalies and triggers corrective actions.",
    version="1.0.0",
)

# Initialize the components
# In a production app, you might manage this differently (e.g., dependency injection)
reflex_map = ReflexMap()
auto_healer = AutoHealer(reflex_map)

class Anomaly(BaseModel):
    """Defines the structure for an incoming anomaly."""
    name: str
    details: Dict[str, Any] = {}

@app.post("/anomaly", status_code=202)
async def receive_anomaly(anomaly: Anomaly):
    """
    Endpoint to receive anomaly notifications from HydraObserver or other sources.
    """
    try:
        print(f"Received anomaly: {anomaly.dict()}")
        auto_healer.handle_anomaly(anomaly.dict())
        return {"status": "Anomaly received and is being processed."}
    except Exception as e:
        # Using HTTPException to return a proper HTTP error response
        # This will be caught and logged by FastAPI's default error handling
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health", status_code=200)
async def health_check():
    """
    Simple health check endpoint to confirm the service is running.
    """
    return {"status": "ok"}

# To run this server:
# uvicorn katana.healer_server:app --reload
