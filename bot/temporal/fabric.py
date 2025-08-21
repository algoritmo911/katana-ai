import networkx as nx
import openai
import json
import os
from .models import EventObject
from typing import Tuple
from bot.zeno.causal_engine import CausalConsistencyEngine

class TimeFabric:
    """
    Структура данных, представляющая собой "ткань времени".
    Хранит события и связи между ними в виде направленного графа.
    """
    def __init__(self):
        self.graph = nx.DiGraph()
        self._openai_client = None
        print("TemporalFabric инициализирована с пустым графом.")

    @property
    def openai_client(self):
        if self._openai_client is None:
            self._openai_client = openai.OpenAI()
        return self._openai_client

    def add_event(self, event: EventObject):
        """
        Добавляет событие в граф как узел 'MemoryEvent'.
        Пытается установить причинно-следственные связи с недавними узлами.
        """
        node_id = event.chronos_id
        attributes = event.model_dump()

        # Pydantic модели нужно конвертировать в строки/числа для атрибутов графа
        attributes['timestamp_utc'] = attributes['timestamp_utc'].isoformat()
        attributes['payload'] = json.dumps(attributes['payload'])

        self.graph.add_node(node_id, label=f"Event: {event.source}", type="MemoryEvent", **attributes)
        print(f"Узел {node_id} добавлен в граф.")

        # Пытаемся связать с недавними событиями
        # (упрощенная логика: связываем с последними N узлами)
        recent_nodes = list(self.graph.nodes())[-10:-1] # последние 9, исключая себя
        for other_node_id in recent_nodes:
            other_node_data = self.graph.nodes[other_node_id]

            # Проверяем причинность только в одном направлении: от старого события к новому.
            # other_node (старый) -> node (новый)
            is_caused, justification, confidence = self._infer_causality(other_node_data, self.graph.nodes[node_id])
            if is_caused:
                self.graph.add_edge(other_node_id, node_id, type="caused", justification=justification, confidence=confidence)
                print(f"Найдена связь: {other_node_id} -> вызвало -> {node_id}")


    def _infer_causality(self, event_a_data: dict, event_b_data: dict) -> Tuple[bool, str, float]:
        """
        Использует LLM для выдвижения гипотезы о причинности, а затем
        CausalConsistencyEngine для ее валидации.
        """
        # 1. Генерируем гипотезу о причинности с помощью LLM
        system_prompt_hypothesis = (
            "You are a logical reasoner. Your task is to determine if Event A could have plausibly caused Event B. "
            "Your response must be a JSON object with 'justification' (max 15 words) and 'confidence' (0.0-1.0)."
        )

        prompt = (
            f"Event A (potential cause): {event_a_data['payload']} at {event_a_data['timestamp_utc']}\n"
            f"Event B (potential effect): {event_b_data['payload']} at {event_b_data['timestamp_utc']}\n\n"
            "Question: If a causal link exists from A to B, provide a brief justification and confidence score."
        )

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt_hypothesis},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            hypothesis = json.loads(response.choices[0].message.content)
            justification = hypothesis.get('justification', '')
            confidence = hypothesis.get('confidence', 0.0)

            if not justification:
                return False, "", 0.0

        except Exception as e:
            print(f"Ошибка при генерации гипотезы о причинности: {e}")
            return False, "", 0.0

        # 2. Валидируем гипотезу с помощью Движка Непротиворечивости
        engine = CausalConsistencyEngine()
        is_consistent = engine.validate(event_a_data, event_b_data, justification)

        if is_consistent:
            return True, justification, confidence
        else:
            return False, "", 0.0

    def save_graph(self, path="analysis_results/temporal_fabric.gml"):
        """Сохраняет граф в файл."""
        print(f"Сохранение графа в {path}...")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        nx.write_gml(self.graph, path)
        print("Граф успешно сохранен.")

    def calculate_gravity_scores(self):
        """
        Рассчитывает 'гравитационные очки' (влиятельность) для каждого события в графе.
        Использует алгоритм PageRank.
        """
        if not self.graph or self.graph.number_of_nodes() == 0:
            print("Граф пуст, невозможно рассчитать гравитацию.")
            return {}

        print("Расчет гравитационных очков (PageRank)...")
        # PageRank рассматривает граф как сеть, где "голоса" передаются по ребрам.
        # Узлы с большим количеством входящих связей от влиятельных узлов получают более высокий ранг.
        gravity_scores = nx.pagerank(self.graph)

        # Сохраняем очки как атрибут узла для последующего использования
        nx.set_node_attributes(self.graph, gravity_scores, 'gravity_score')
        print("Гравитационные очки рассчитаны и добавлены в атрибуты узлов.")
        return gravity_scores

    def get_attention_window(self, event_chronos_id: str, k: int = 5):
        """
        Возвращает 'окно внимания': k наиболее связанных событий для данного.
        Простой подход: берет соседей первого и второго порядка.
        """
        if event_chronos_id not in self.graph:
            return []

        # Собираем соседей первого порядка (входящие и исходящие)
        neighbors = set(self.graph.predecessors(event_chronos_id))
        neighbors.update(self.graph.successors(event_chronos_id))

        # Добавляем соседей второго порядка для расширения контекста
        second_order_neighbors = set()
        for neighbor in list(neighbors):
            second_order_neighbors.update(self.graph.predecessors(neighbor))
            second_order_neighbors.update(self.graph.successors(neighbor))

        neighbors.update(second_order_neighbors)

        # Удаляем исходный узел, если он попал в соседи
        neighbors.discard(event_chronos_id)

        # Сортируем соседей по их 'гравитации'
        sorted_neighbors = sorted(
            list(neighbors),
            key=lambda node_id: self.graph.nodes[node_id].get('gravity_score', 0),
            reverse=True
        )

        return sorted_neighbors[:k]
