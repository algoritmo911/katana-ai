import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import os
import asyncio

# Add bot directory to sys.path to allow imports from bot.nlp_service
# This is a common way to handle imports from sibling directories,
# though for larger projects, proper packaging is recommended.
current_dir = Path(__file__).resolve().parent
bot_dir = current_dir / "bot"
sys.path.append(str(bot_dir.parent)) # Add the root directory ('katana-ai-project') to sys.path

from bot.nlp_service import NLPService, DEFAULT_FALLBACK_RESPONSE

# Initialize FastAPI app
app = FastAPI(title="Katana AI API", version="0.1.0")

# Initialize NLP Service
# Ensure OPENAI_API_KEY is set in your environment for NLPService to work
nlp_service = NLPService()

# Configure CORS
# Allows all origins, methods, and headers for development.
# For production, restrict origins to your frontend's domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specify your frontend origin e.g. "http://localhost:3000"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request and response
class MessageRequest(BaseModel):
    text: str
    # Potentially add user_id, session_id, etc. in the future
    # model: str | None = None # Example: allow choosing NLP model via API

class MessageResponse(BaseModel):
    response: str
    # error: str | None = None # If you want to include error details in response body

@app.post("/api/message", response_model=MessageResponse)
async def handle_message_api(request: MessageRequest):
    """
    Handles a user's message, gets a response from the NLP service,
    and returns it.
    """
    if not request.text:
        # You could raise HTTPException for bad input, or return a specific error response
        # For consistency with NLPService's fallback, let's return a fallback.
        # raise HTTPException(status_code=400, detail="Input text cannot be empty.")
        return MessageResponse(response="Input text cannot be empty.")

    try:
        # NLPService's get_chat_completion is async
        nlp_response_text = await nlp_service.get_chat_completion(request.text)

        if nlp_response_text is None: # Should be handled by NLPService's own fallbacks
            nlp_response_text = DEFAULT_FALLBACK_RESPONSE # Use the same default as NLPService

        return MessageResponse(response=nlp_response_text)
    except Exception as e:
        # Log the exception for server-side debugging
        print(f"API Error: Exception during NLP processing: {e}", file=sys.stderr) # Or use proper logging
        # Return a generic error response to the client
        # Avoid exposing detailed internal errors to the client directly
        raise HTTPException(status_code=500, detail="An internal error occurred while processing your message.")

@app.get("/")
async def read_root():
    return {"message": "Katana AI API is running. Send POST requests to /api/message"}

# from pathlib import Path # This was already imported at the top

if __name__ == "__main__":
    # This allows running the server directly with `python api_server.py`
    # Uvicorn will run on http://127.0.0.1:8000 by default
    # Ensure OPENAI_API_KEY is available in the environment where this server runs.
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY is not set. NLP functionality will likely fail.", file=sys.stderr)

    uvicorn.run(app, host="0.0.0.0", port=8000)
