import spacy
import textstat
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# A simple way to share the loaded models without reloading them every time.
_nlp = None
_sentiment_analyzer = None

def get_nlp_model():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp

def get_sentiment_analyzer():
    global _sentiment_analyzer
    if _sentiment_analyzer is None:
        _sentiment_analyzer = SentimentIntensityAnalyzer()
    return _sentiment_analyzer

class LinguisticSensor:
    """
    Analyzes the linguistic properties of a text to infer operator state.
    """
    def __init__(self):
        # Ensure models are loaded on instantiation
        self.nlp = get_nlp_model()
        self.sentiment_analyzer = get_sentiment_analyzer()

    def _calculate_imperative_score(self, doc) -> float:
        """
        Calculates the ratio of imperative verbs to total verbs.
        A higher score suggests a more command-oriented tone.
        """
        verb_count = 0
        imperative_count = 0
        for token in doc:
            if token.pos_ == "VERB":
                verb_count += 1
                # spaCy's dependency parser can identify imperative verbs (often root of the sentence)
                if token.dep_ == "ROOT" and token.tag_ == "VB":
                    imperative_count += 1

        if verb_count == 0:
            return 0.0

        return imperative_count / verb_count

    def analyze(self, text: str):
        """
        Performs a full linguistic analysis on the input text.
        """
        # We need to import the contract here to avoid circular dependencies
        # if other sensors were to ever use this one.
        from ..contracts import LinguisticFeatures

        doc = self.nlp(text)

        # 1. Calculate imperative score
        imperative_score = self._calculate_imperative_score(doc)

        # 2. Calculate complexity score
        # Flesch reading ease: higher is easier. We want higher to be more complex.
        # We normalize it to a 0-1 range where 1 is very complex.
        ease = textstat.flesch_reading_ease(text)
        complexity_score = max(0.0, 1.0 - (ease / 100.0))

        # 3. Calculate sentiment score
        sentiment_score = self.sentiment_analyzer.polarity_scores(text)['compound']

        # 4. Calculate terseness score
        # We use a simple inverse relationship with the number of words.
        # The '+ 4' in the denominator is a smoothing factor to prevent extreme scores for 1-2 word inputs.
        word_count = len(text.split())
        terseness_score = 1.0 / (word_count + 4) * 4 # Normalize to be higher for fewer words

        return LinguisticFeatures(
            imperative_score=imperative_score,
            complexity_score=complexity_score,
            sentiment_score=sentiment_score,
            terseness_score=terseness_score
        )

if __name__ == '__main__':
    # A simple test harness to demonstrate the sensor.
    sensor = LinguisticSensor()

    text1 = "Jules, get me the report for the last 24 hours. And be quick about it."
    features1 = sensor.analyze(text1)
    print(f"Text 1: '{text1}'")
    print(f"Features 1: {features1.model_dump_json(indent=2)}\n")

    text2 = "I was wondering if you might be able to help me explore some options for refactoring the authentication module? No rush at all."
    features2 = sensor.analyze(text2)
    print(f"Text 2: '{text2}'")
    print(f"Features 2: {features2.model_dump_json(indent=2)}\n")

    text3 = "This is utter garbage. The performance is terrible and the code is a mess."
    features3 = sensor.analyze(text3)
    print(f"Text 3: '{text3}'")
    print(f"Features 3: {features3.model_dump_json(indent=2)}\n")
