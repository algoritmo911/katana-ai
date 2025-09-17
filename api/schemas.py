from pydantic import BaseModel
from typing import List, Dict, Any

class SessionStartResponse(BaseModel):
    """Response model for starting a new session."""
    session_id: str

class QueryRequest(BaseModel):
    """Request model for sending a query."""
    text: str

class QueryResponse(BaseModel):
    """Response model for a query."""
    reply: str
    intent_object: Dict[str, Any]

class HistoryTurn(BaseModel):
    """A single turn in the conversation history."""
    user: str
    bot: str

class HistoryResponse(BaseModel):
    """Response model for conversation history."""
    session_id: str
    history: List[HistoryTurn]
