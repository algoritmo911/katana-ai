# -*- coding: utf-8 -*-
"""
HydraObserver

Observes and reports on the underlying infrastructure metrics for each service,
such as CPU and memory usage.
"""
import random

def get_infra_metrics(service_name: str) -> dict:
    """
    Returns a dictionary of mock infrastructure metrics for a given service.
    In a real system, this would query a monitoring tool like Prometheus.
    """
    # Using service_name hash to add some deterministic pseudo-randomness
    base_cpu = (hash(service_name) % 10)
    base_mem = (hash(service_name) % 256)

    return {
        "cpu": round(base_cpu + random.uniform(0.0, 15.0), 2),
        "memory": round(base_mem + random.uniform(50.0, 250.0), 2),
    }
