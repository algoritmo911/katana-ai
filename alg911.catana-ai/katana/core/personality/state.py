"""
Psychometric Core: The mathematical model of Katana's personality state.
"""
from pydantic import BaseModel, Field

class PersonalityState(BaseModel):
    """
    Represents the personality state based on the "Big Five" (OCEAN) model.
    Each trait is a float between 0.0 and 1.0.
    """
    openness: float = Field(..., ge=0.0, le=1.0, description="Открытость опыту (Openness to Experience)")
    conscientiousness: float = Field(..., ge=0.0, le=1.0, description="Добросовестность (Conscientiousness)")
    extraversion: float = Field(..., ge=0.0, le=1.0, description="Экстраверсия (Extraversion)")
    agreeableness: float = Field(..., ge=0.0, le=1.0, description="Доброжелательность (Agreeableness)")
    neuroticism: float = Field(..., ge=0.0, le=1.0, description="Невротизм (Neuroticism)")

# The default personality profile for Katana.
# High Conscientiousness for reliability and diligence.
# Low Neuroticism for emotional stability.
# Moderately high Openness and Agreeableness for adaptability and cooperation.
# Neutral Extraversion.
DEFAULT_PERSONALITY = PersonalityState(
    openness=0.6,
    conscientiousness=0.9,
    extraversion=0.5,
    agreeableness=0.7,
    neuroticism=0.2,
)
