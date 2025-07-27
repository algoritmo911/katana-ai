from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.katana_core.predictor import Predictor
from src.memory.memory_manager import MemoryManager

app = FastAPI()
predictor = Predictor(memory_manager=MemoryManager())

class PredictRequest(BaseModel):
    chat_id: str
    steps: int = 10
    model_name: str = 'arima'

@app.post("/predict/")
def predict(request: PredictRequest):
    try:
        data, timestamps = predictor.fetch_data_from_memory(request.chat_id)
        predictor.ingest(data, timestamps)

        # Set the model
        predictor.model_name = request.model_name

        forecast = predictor.predict(steps=request.steps)
        return {"forecast": forecast}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
