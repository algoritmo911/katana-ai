from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles

app = FastAPI()

class EchoRequest(BaseModel):
    message: str

class EchoResponse(BaseModel):
    response: str

@app.get("/health")
async def health_check():
    return {"status": "alive"}

@app.post("/api/v1/echo", response_model=EchoResponse)
async def echo(request: EchoRequest):
    return EchoResponse(response=request.message)

app.mount("/", StaticFiles(directory="../ui/dist", html=True), name="static")
