from abc import ABC, abstractmethod
from pydantic import BaseModel

class Intent(BaseModel):
    """
    Represents the user's recognized intent and extracted entities.
    """
    name: str
    entities: dict

class AbstractNLPService(ABC):
    """
    Abstract contract for all NLP service providers.
    """
    @abstractmethod
    async def parse_intent(self, text: str) -> Intent:
        """
        Parses the user's text to extract an intent and any relevant entities.

        Args:
            text: The raw text from the user.

        Returns:
            An Intent object. If no intent is found, it might return a default
            'unknown' intent.
        """
        pass


class RuleBasedNLPService(AbstractNLPService):
    """
    A simple NLP service that uses keyword matching to determine intent.
    """
    def __init__(self, rules: dict[str, list[str]] | None = None):
        if rules is None:
            # These are the intents mentioned in the epic.
            self.rules = {
                "status": ["статус", "status"],
                "analyze": ["анализ", "analyze", "проанализируй"],
                "think": ["думай", "think", "подумай"],
            }
        else:
            self.rules = rules

    async def parse_intent(self, text: str) -> Intent:
        """
        Parses text by checking for keywords defined in the rules.
        """
        text_lower = text.lower()
        for intent_name, keywords in self.rules.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return Intent(name=intent_name, entities={})

        return Intent(name="unknown", entities={"original_text": text})
