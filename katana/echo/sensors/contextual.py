import spacy
from typing import List

# A simple way to share the loaded model without reloading it every time.
_nlp = None

def get_nlp_model():
    global _nlp
    if _nlp is None:
        # We need a medium or large model for good vectors.
        # Let's check if one is available, otherwise fall back.
        try:
            _nlp = spacy.load("en_core_web_md")
        except OSError:
            print("WARNING: en_core_web_md not found. Falling back to en_core_web_sm. Context vectors will be less accurate.")
            _nlp = spacy.load("en_core_web_sm")
    return _nlp

class ContextualSensor:
    """
    Analyzes the text to determine the topic of conversation or focus.
    """
    def __init__(self):
        self.nlp = get_nlp_model()

    def analyze(self, text: str):
        """
        Extracts key entities and a context vector from the text.
        """
        from ..contracts import ContextualFeatures

        doc = self.nlp(text)

        # Extract named entities
        entities = [ent.text for ent in doc.ents]

        # Get the document vector
        # Note: en_core_web_sm may not have good vectors.
        context_vector = doc.vector.tolist() if doc.has_vector else []

        return ContextualFeatures(
            entities=entities,
            context_vector=context_vector
        )

if __name__ == '__main__':
    # We need to download the medium model for this test to be effective.
    # This is a placeholder to show it runs.
    try:
        spacy.load("en_core_web_md")
    except OSError:
        print("Downloading en_core_web_md for testing...")
        import os
        os.system("python3 -m spacy download en_core_web_md")

    sensor = ContextualSensor()
    text = "I need to analyze the performance of the Morpheus Protocol, specifically the REMExecutor component in katana."
    features = sensor.analyze(text)

    print(f"Text: '{text}'")
    print(f"Features: {features.model_dump_json(indent=2)}")
    print(f"(Vector dimension: {len(features.context_vector)})")
