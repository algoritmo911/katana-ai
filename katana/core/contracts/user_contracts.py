import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, EmailStr


class UserRole(str, Enum):
    """User roles."""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class CreateUserContract(BaseModel):
    """
    Contract for creating a new user.
    Used as a sample for the test generation system.
    """
    user_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="The username for the new user."
    )
    email: EmailStr = Field(..., description="The user's email address.")
    full_name: Optional[str] = Field(None, max_length=100, description="The user's full name.")
    is_active: bool = Field(True, description="Whether the user account is active.")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    roles: List[UserRole] = Field(..., min_items=1, description="A list of roles assigned to the user.")
    profile_data: dict = Field({}, description="Arbitrary profile data for the user.")
