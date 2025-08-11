from pydantic import BaseModel

class SpecialistProfile(BaseModel):
    username: str
    technical_skills: list[str]
    cognitive_score: float
