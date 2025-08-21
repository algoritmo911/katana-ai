import numpy as np
from datetime import datetime
import openai
import json

class CausalConsistencyEngine:
    """
    Движок для валидации причинно-следственных связей, предложенных LLM.
    Заменяет хрупкие детерминированные тесты на семантическую и логическую проверку.
    """
    def __init__(self):
        self._openai_client = None
        self.similarity_threshold = 0.4 # Порог для семантической связи

    @property
    def openai_client(self):
        if self._openai_client is None:
            self._openai_client = openai.OpenAI()
        return self._openai_client

    def _validate_temporal_order(self, timestamp_a: str, timestamp_b: str) -> bool:
        """Проверяет, что событие A произошло раньше события B."""
        try:
            time_a = datetime.fromisoformat(timestamp_a.replace('Z', '+00:00'))
            time_b = datetime.fromisoformat(timestamp_b.replace('Z', '+00:00'))
            return time_a < time_b
        except (ValueError, TypeError):
            return False # Не можем сравнить, если формат неверный

    def _get_semantic_similarity(self, embedding_a: np.ndarray, embedding_b: np.ndarray) -> float:
        """Вычисляет косинусное сходство между эмбеддингами."""
        if embedding_a.size == 0 or embedding_b.size == 0:
            return 0.0

        cosine_sim = np.dot(embedding_a, embedding_b) / (np.linalg.norm(embedding_a) * np.linalg.norm(embedding_b))
        return cosine_sim

    def validate(self, event_a_data: dict, event_b_data: dict, justification: str) -> bool:
        """
        Полный цикл валидации для причинно-следственной связи.
        Передает все проверки в LLM для принятия финального решения.
        """
        print(f"Валидация связи: {event_a_data['event_id']} -> {event_b_data['event_id']}...")

        # 1. Темпоральная проверка
        temporal_ok = self._validate_temporal_order(event_a_data['timestamp_utc'], event_b_data['timestamp_utc'])

        # 2. Семантическая проверка (получаем скор, а не bool)
        embedding_a = np.array(json.loads(event_a_data.get('embedding', '[]')))
        embedding_b = np.array(json.loads(event_b_data.get('embedding', '[]')))
        similarity_score = self._get_semantic_similarity(embedding_a, embedding_b)

        # 3. Финальная проверка логики с помощью LLM
        system_prompt = (
            "You are a meticulous logical reasoner. Your task is to determine if a proposed causal link is valid "
            "based on raw evidence. The final decision is yours. A 'cause' MUST happen before its 'effect'. "
            "A high semantic similarity score suggests a strong relationship, but is not definitive. "
            "A low score suggests a weak relationship, but context can still imply causality. "
            "Answer only with 'true' or 'false'."
        )
        prompt = (
            "Analyze the following data to determine if Event A plausibly caused Event B. "
            "Pay close attention to how fields in Event B's payload might reference Event A's ID.\n\n"
            f"Event A:\n"
            f"  ID: {event_a_data['event_id']}\n"
            f"  Source: {event_a_data['source']}\n"
            f"  Payload: {event_a_data['payload']}\n\n"
            f"Event B:\n"
            f"  ID: {event_b_data['event_id']}\n"
            f"  Source: {event_b_data['source']}\n"
            f"  Payload: {event_b_data['payload']}\n\n"
            f"Proposed Justification by another AI: '{justification}'\n\n"
            "**Evidence:**\n"
            f"- Event A happened before Event B: {temporal_ok}\n"
            f"- Semantic Similarity Score (0.0 to 1.0): {similarity_score:.4f}\n\n"
            "Final Question: Based on all evidence and the justification, is the causal link from A to B logical and consistent? Answer 'true' or 'false'."
        )

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0
            )
            decision = response.choices[0].message.content.lower().strip()
            is_consistent = "true" in decision

            if is_consistent:
                print("Вердикт движка: Связь логична и непротиворечива.")
            else:
                print("Вердикт движка: Связь НЕ является логичной.")

            return is_consistent
        except Exception as e:
            print(f"Ошибка при LLM-валидации: {e}")
            return False
