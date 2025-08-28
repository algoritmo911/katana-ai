from fastapi import FastAPI
from pydantic import BaseModel

from katana_single_app.services.nlp_service import RuleBasedNLPService
from katana_single_app.core import handle_intent

app = FastAPI(
    title="Katana 'Chimera' Protocol",
    version="1.0",
    description="Layer 1: Sentient Listener",
)

nlp_service = RuleBasedNLPService()

class CommandRequest(BaseModel):
    text: str

class CommandResponse(BaseModel):
    response: str

@app.post("/api/v1/command", response_model=CommandResponse)
async def process_command(request: CommandRequest):
    """
    Receives a text command, parses the intent, handles it, and returns a response.
    This is the main entry point for the Katana cognitive loop.
    """
    # 1. Parse Intent
    intent = await nlp_service.parse_intent(request.text)

    # 2. Handle Intent
    response_text = await handle_intent(intent)

    # 3. Return Response
    return {"response": response_text}
