from abc import ABC, abstractmethod

class NLPProvider(ABC):
    """
    Abstract Base Class for NLP providers.
    All NLP provider implementations should inherit from this class
    and implement its abstract methods.
    """

    @abstractmethod
    def get_intent(self, text: str) -> dict:
        """
        Processes the input text and returns the identified intent and confidence.

        Args:
            text: The user's input string.

        Returns:
            A dictionary, e.g., {"intent_name": "greeting", "confidence": 0.95}
            Returns an empty dictionary or a dictionary with a default "unknown_intent"
            if no intent can be reliably identified.
        """
        pass

    @abstractmethod
    def get_slots(self, text: str, intent: str = None) -> dict:
        """
        Processes the input text (and optionally a pre-identified intent)
        to extract relevant slots (entities).

        Args:
            text: The user's input string.
            intent: (Optional) The intent identified for this text.
                    Some providers might use this to improve slot extraction.

        Returns:
            A dictionary of extracted slots, e.g.,
            {"location": "New York", "date": "tomorrow"}
            Returns an empty dictionary if no slots are found.
        """
        pass

    @abstractmethod
    def process(self, text: str) -> dict:
        """
        Processes the input text to get both intent and slots.
        This can be more efficient for some providers than calling
        get_intent and get_slots separately.

        Args:
            text: The user's input string.

        Returns:
            A dictionary containing both intent and slots, e.g.,
            {
                "intent": {"intent_name": "book_flight", "confidence": 0.88},
                "slots": {"destination": "London", "departure_date": "2024-12-25"}
            }
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Returns the name of the NLP provider.
        """
        pass
