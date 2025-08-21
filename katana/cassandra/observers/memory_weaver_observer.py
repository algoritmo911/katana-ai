# -*- coding: utf-8 -*-
"""
MemoryWeaverObserver

Observes and reports on the state of the MemoryWeaver component,
specifically the dynamics of the knowledge graph.
"""
import random

def get_knowledge_graph_metrics(service_name: str) -> dict:
    """
    Returns a dictionary of mock metrics related to the knowledge graph.
    In a real system, this would query the MemoryWeaver service's API.
    """
    # This is a placeholder for a more complex metric in the future.
    # We are observing the 'neurovault-api' as it's the most likely
    # candidate to be related to the knowledge graph.
    if service_name == "neurovault-api":
        return {
            "kg_growth_rate": round(random.uniform(0.1, 1.5), 3)
        }
    return {}
