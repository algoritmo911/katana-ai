import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from pydantic import BaseModel, Field

def get_utc_now():
    """Returns the current time in UTC."""
    return datetime.now(timezone.utc)

class GestaltEvent(BaseModel):
    """
    A standardized data structure for all events flowing through the Gestalt system.
    """
    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    timestamp: datetime = Field(default_factory=get_utc_now)
    source_id: str = Field(..., description="The unique identifier of the sensor that generated this event.")
    content: Any = Field(..., description="The raw data or content of the event.")

    # The 'valence' field will be populated by the sentiment analysis module.
    # It represents the emotional "charge" of the event.
    valence: Optional[float] = Field(None, description="The emotional valence score of the event, from -1.0 (negative) to 1.0 (positive).")

    class Config:
        # Pydantic configuration
        # Allow arbitrary types for content, though it will often be a string.
        arbitrary_types_allowed = True
        # Make the model immutable after creation to prevent accidental changes.
        frozen = True
