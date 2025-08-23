import uvicorn
from fastapi import FastAPI

app = FastAPI(
    title="Prometheus Orchestrator",
    description="The brain and will of the system.",
    version="0.1-alpha",
)

@app.get("/health", tags=["Monitoring"])
async def health_check():
    """
    Checks if the orchestrator is running.
    """
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
