import re
from typing import Dict, List, Tuple, Optional

from sentence_transformers import SentenceTransformer, util
import torch

from nlp.tool_registry import ToolRegistry, ToolContract

class EmbeddingClassifier:
    """
    Classifies user intent by comparing the embedding of their message with
    the embeddings of the descriptions of available tools.
    """
    def __init__(self, tool_registry: ToolRegistry, model_name: str = 'all-MiniLM-L6-v2'):
        self.tool_registry = tool_registry
        self.model = SentenceTransformer(model_name)
        self.tool_names: List[str] = []
        self.tool_embeddings: Optional[torch.Tensor] = None
        self._prepare_tool_embeddings()

    def _prepare_tool_embeddings(self):
        """
        Generates and caches embeddings for the descriptions of all registered tools.
        """
        tools = self.tool_registry.get_all_tools()
        if not tools:
            return

        self.tool_names = [tool.name for tool in tools]
        descriptions = [tool.description for tool in tools]
        self.tool_embeddings = self.model.encode(descriptions, convert_to_tensor=True)

    def classify(self, text: str) -> Optional[Tuple[str, float]]:
        """
        Finds the most similar tool for the given text based on cosine similarity.

        Returns:
            A tuple of (tool_name, confidence_score) or None if no tools are registered.
        """
        if self.tool_embeddings is None or not self.tool_names:
            return None

        text_embedding = self.model.encode(text, convert_to_tensor=True)

        # Compute cosine similarity
        cosine_scores = util.cos_sim(text_embedding, self.tool_embeddings)

        # Find the best match
        best_match_idx = torch.argmax(cosine_scores)
        best_score = cosine_scores[0][best_match_idx].item()

        best_tool_name = self.tool_names[best_match_idx]

        return best_tool_name, best_score

def parse_hard_commands(text: str) -> Optional[str]:
    """
    Parses for exact, hard-coded commands like /start or /help.
    This is the fastest check and should be done first.
    """
    # Simple example, can be expanded with a proper command registry
    if text.strip().lower() == '/help':
        return 'show_help' # This would be a registered tool name
    if text.strip().lower() == '/status':
        return 'get_system_status'
    return None


class IntentClassifier:
    """
    The main classifier that orchestrates the cascading logic.
    """
    def __init__(self, tool_registry: ToolRegistry, embedding_confidence_threshold: float = 0.7):
        self.embedding_classifier = EmbeddingClassifier(tool_registry)
        self.embedding_confidence_threshold = embedding_confidence_threshold

    def classify(self, text: str) -> Dict[str, any]:
        """
        Classifies the user's intent using a cascading approach.

        1. Check for hard-coded commands.
        2. Use the embedding classifier.
        3. (Placeholder) Escalate to LLM if confidence is low.

        Returns:
            A dictionary containing the classification result, e.g.,
            {'type': 'tool', 'name': 'tool_name', 'source': 'embedding_classifier'}
            {'type': 'escalate_llm', 'reason': 'low_confidence', 'source': 'intent_classifier'}
        """
        # 1. Hard-coded commands
        hard_command = parse_hard_commands(text)
        if hard_command:
            return {'type': 'tool', 'name': hard_command, 'source': 'hard_command'}

        # 2. Embedding classifier
        classification_result = self.embedding_classifier.classify(text)
        if classification_result:
            tool_name, score = classification_result
            if score >= self.embedding_confidence_threshold:
                return {'type': 'tool', 'name': tool_name, 'score': score, 'source': 'embedding_classifier'}
            else:
                # 3. Escalate to LLM
                return {
                    'type': 'escalate_llm',
                    'reason': f'Embedding similarity score ({score:.2f}) is below threshold ({self.embedding_confidence_threshold}).',
                    'source': 'intent_classifier'
                }

        # Default fallback: if no tools or classifiers are available
        return {'type': 'escalate_llm', 'reason': 'No classification methods available.', 'source': 'intent_classifier'}
