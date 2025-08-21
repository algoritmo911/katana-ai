import logging
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    """
    A wrapper around a sentiment analysis library to provide a consistent
    interface for calculating emotional valence.
    """

    def __init__(self):
        """
        Initializes the sentiment analyzer.
        """
        try:
            self.analyzer = SentimentIntensityAnalyzer()
            logger.info("VADER SentimentIntensityAnalyzer initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize SentimentIntensityAnalyzer: {e}", exc_info=True)
            self.analyzer = None

    def get_valence(self, text: str) -> float | None:
        """
        Calculates the emotional valence of a given text.

        :param text: The text to analyze.
        :return: A float between -1.0 (most negative) and 1.0 (most positive),
                 or None if analysis is not possible.
        """
        if not self.analyzer:
            logger.warning("Sentiment analyzer not available. Cannot calculate valence.")
            return None

        if not isinstance(text, str) or not text.strip():
            # VADER can handle non-string types, but we want to be explicit.
            # It returns 0.0 for empty strings, which is neutral, and that's fine.
            return 0.0

        try:
            # The polarity_scores() method returns a dict:
            # {'neg': 0.0, 'neu': 0.326, 'pos': 0.674, 'compound': 0.7579}
            # The 'compound' score is the normalized, weighted composite score.
            scores = self.analyzer.polarity_scores(text)
            return scores['compound']
        except Exception as e:
            logger.error(f"Error during sentiment analysis for text: '{text[:50]}...': {e}", exc_info=True)
            return None
