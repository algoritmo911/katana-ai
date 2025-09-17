import uvicorn
import uuid
from fastapi import FastAPI, HTTPException, Depends, Request, status
from typing import Dict

from bot.katana_bot import KatanaBot
from . import schemas
from . import security
from .logger import log

# --- App Initialization ---
app = FastAPI(
    title="Katana Cognitive Core API",
    description="API Gateway for the Katana NLP Cognitive Core.",
    version="1.0.0",
)

# In-memory storage for bot instances
sessions: Dict[str, KatanaBot] = {}

from fastapi.responses import JSONResponse

# --- Middleware and Exception Handlers ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
    log.info(f"Request: {request.method} {request.url.path}")
    response = await call_next(request)
    log.info(f"Response: {response.status_code}")
    return response

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    log.error(f"Unhandled exception for {request.method} {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."},
    )

# --- Endpoints ---

@app.get("/", tags=["Status"])
async def read_root():
    """Root endpoint to check API status."""
    return {"status": "Katana Cognitive Core API is running."}

@app.post("/session/start", response_model=schemas.SessionStartResponse, tags=["Session Management"])
async def start_session():
    """
    Initializes a new conversation session and returns a unique session_id.
    """
    session_id = str(uuid.uuid4())
    log.info(f"Starting new session: {session_id}")
    # KatanaBot is now instantiated without telebot for API usage
    sessions[session_id] = KatanaBot(use_telebot=False)
    return {"session_id": session_id}

@app.post("/session/{session_id}/query", response_model=schemas.QueryResponse, tags=["Conversation"], dependencies=[Depends(security.get_api_key)])
async def post_query(session_id: str, request: schemas.QueryRequest):
    """
    Processes a user's query within a given session using the refactored bot logic.
    """
    log.info(f"Query received for session: {session_id}")
    if session_id not in sessions:
        log.warning(f"Session not found: {session_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    bot_instance = sessions[session_id]

    try:
        # The entire logic is now encapsulated in the bot's method
        result = bot_instance.process_chat_message(session_id, request.text)

        log.info(f"Successfully processed query for session: {session_id}")
        return schemas.QueryResponse(
            reply=result["reply"],
            intent_object=result["intent_object"]
        )
    except Exception as e:
        log.error(f"An error occurred while processing query for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal error occurred.")

@app.get("/session/{session_id}/history", response_model=schemas.HistoryResponse, tags=["Session Management"], dependencies=[Depends(security.get_api_key)])
async def get_history(session_id: str):
    """
    Retrieves the conversation history for a given session.
    """
    log.info(f"History requested for session: {session_id}")
    if session_id not in sessions:
        log.warning(f"Session not found: {session_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    bot_instance = sessions[session_id]
    # The history is stored within the bot's session dictionary
    history = bot_instance.sessions.get(session_id, {}).get("history", [])

    # The history in the bot is already in the correct format for HistoryTurn
    return schemas.HistoryResponse(session_id=session_id, history=history)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
