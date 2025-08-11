from datetime import date
from typing import List

from pydantic import BaseModel, Field


class SpecialistProfile(BaseModel):
    """
    Represents the professional profile of a specialist, including their
    technical skills and recent activity.
    """
    github_username: str
    languages: List[str]
    skill_level: int = Field(
        ...,
        ge=1,
        le=10,
        description="An estimated skill level from 1 (beginner) to 10 (expert)."
    )
    last_commit_date: date
