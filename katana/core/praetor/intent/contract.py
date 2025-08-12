"""
Defines the data structure for an Intent Contract, which formalizes
a high-level goal into a machine-readable format.
"""
from typing import List
from pydantic import BaseModel, Field, constr


class IntentContract(BaseModel):
    """
    A Pydantic model representing a formalized "Intent Contract".

    This structure captures a high-level objective, its boundaries, and
    the conditions for its successful completion. It serves as the
    foundational "law" for all subsequent AI-driven strategic planning
    and execution within the Praetor system.
    """

    goal: constr(min_length=1) = Field(
        ...,
        description="A clear, concise statement of the primary objective. "
                    "This is the 'what' and 'why' of the mission. Cannot be empty."
    )

    constraints: List[constr(min_length=1)] = Field(
        default_factory=list,
        description="A list of rules, limitations, or boundaries that must be "
                    "adhered to. Can be empty, but strings within it cannot."
    )

    success_criteria: List[constr(min_length=1)] = Field(
        ...,
        min_items=1,
        description="A non-empty list of specific, measurable, and verifiable "
                    "success conditions. Strings within the list cannot be empty."
    )

    class Config:
        """Pydantic model configuration."""
        extra = "forbid"
        str_strip_whitespace = True
        json_schema_extra = {
            "title": "Intent Contract",
            "description": "A formalized contract that translates a natural language "
                         "goal into a structured, verifiable, and executable format "
                         "for the Praetor system.",
            "examples": [
                {
                    "goal": "Increase user retention by 5% in the next quarter.",
                    "constraints": [
                        "Budget must not exceed $50,000.",
                        "Must not negatively impact user experience for the premium segment.",
                        "Comply with GDPR and all data privacy regulations."
                    ],
                    "success_criteria": [
                        "Achieve a 5% increase in the 30-day rolling retention rate for active users.",
                        "The change must be validated by an A/B test with 95% statistical significance.",
                        "Deployment must be completed before the end of Q3."
                    ]
                }
            ]
        }
