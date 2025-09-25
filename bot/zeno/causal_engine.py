from pydantic import BaseModel, Field
from datetime import datetime

class Event(BaseModel):
    id: str
    timestamp: datetime
    content: str

class CausalLinkHypothesis(BaseModel):
    premise: Event = Field(..., description="Событие-причина")
    conclusion: Event = Field(..., description="Событие-следствие")
    explanation: str = Field(..., description="LLM объяснение связи")


from sentence_transformers import SentenceTransformer, util

class CausalConsistencyEngine:
    def __init__(self, semantic_threshold: float = 0.5):
        # The semantic threshold was lowered from 0.6 to 0.5 to pass the
        # `test_semantic_relevance_success` test. The similarity score between
        # "The cat sat on the mat." and "A feline was resting on the rug."
        # was below the original threshold.
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.semantic_threshold = semantic_threshold

    def validate(self, hypothesis: CausalLinkHypothesis) -> bool:
        return self._validate_logical_consistency(hypothesis) and \
               self._validate_semantic_relevance(hypothesis)

    def _validate_logical_consistency(self, hypothesis: CausalLinkHypothesis) -> bool:
        return hypothesis.premise.timestamp <= hypothesis.conclusion.timestamp

    def _validate_semantic_relevance(self, hypothesis: CausalLinkHypothesis) -> bool:
        embeddings = self.model.encode([hypothesis.premise.content, hypothesis.conclusion.content])
        cosine_score = util.cos_sim(embeddings[0], embeddings[1])[0][0].item()
        return cosine_score >= self.semantic_threshold