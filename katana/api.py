from fastapi import FastAPI
from .monitoring import get_stats, get_uptime

app = FastAPI()

@app.get("/api/katana/health")
def health_check():
    return {"status": "ok", "uptime": get_uptime()}

@app.get("/api/katana/stats")
def get_katana_stats():
    return get_stats()
