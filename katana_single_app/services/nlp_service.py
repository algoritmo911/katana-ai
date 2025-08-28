from abc import ABC, abstractmethod
from pydantic import BaseModel

class Intent(BaseModel):
    """
    Represents the user's intent, extracted from their text.
    """
    name: str
    entities: dict
    original_text: str

class AbstractNLPService(ABC):
    """
    Abstract contract for all NLP providers.
    """
    @abstractmethod
    async def parse_intent(self, text: str) -> Intent:
        """
        Parses the user's text to extract an intent and entities.
        """
        pass


class RuleBasedNLPService(AbstractNLPService):
    """
    A simple NLP service that uses keyword matching to determine intent.
    """
    async def parse_intent(self, text: str) -> Intent:
        """
        Parses intent based on keywords.

        - 'статус' -> status
        - 'анализ'/'анализируй' -> analyze
        - 'думай'/'мысли' -> think
        - Defaults to 'unknown'.
        """
        text_lower = text.lower()
        intent_name = "unknown"

        if "статус" in text_lower:
            intent_name = "status"
        elif "анализ" in text_lower or "анализируй" in text_lower:
            intent_name = "analyze"
        elif "думай" in text_lower or "мысли" in text_lower:
            intent_name = "think"

        return Intent(
            name=intent_name,
            entities={},
            original_text=text
        )
