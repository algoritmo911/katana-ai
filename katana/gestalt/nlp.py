import logging
import re
from typing import Set

logger = logging.getLogger(__name__)

class EntityExtractor:
    """
    A simple NLP module for extracting predefined entities from text.
    """

    def __init__(self, keywords: list[str]):
        """
        Initializes the entity extractor with a list of keywords.

        :param keywords: A list of strings to search for as entities.
        """
        if not keywords:
            logger.warning("EntityExtractor initialized with no keywords.")
            self.keywords = []
            self.pattern = None
        else:
            # We build a single regex pattern for efficiency.
            # The pattern looks for whole words (using word boundaries \b)
            # and is case-insensitive.
            self.keywords = [kw.lower() for kw in keywords]
            # Escape special regex characters in keywords and join them with OR |
            regex_parts = [re.escape(kw) for kw in self.keywords]
            self.pattern = re.compile(r'\b(' + '|'.join(regex_parts) + r')\b', re.IGNORECASE)
            logger.info(f"EntityExtractor initialized with {len(self.keywords)} keywords.")

    def extract_entities(self, text: str) -> Set[str]:
        """
        Extracts all unique keywords found in the given text.

        :param text: The text to analyze.
        :return: A set of unique entities found in the text (normalized to lowercase).
        """
        if not self.pattern or not isinstance(text, str):
            return set()

        try:
            # Find all non-overlapping matches and convert them to lowercase.
            # Using a set comprehension for efficiency and to ensure uniqueness.
            return {match.lower() for match in self.pattern.findall(text)}
        except Exception as e:
            logger.error(f"Error during entity extraction for text: '{text[:50]}...': {e}", exc_info=True)
            return set()
