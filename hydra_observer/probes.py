import logging
import psutil
import time
from hydra_observer.reactor.reaction_core import reaction_core
from hydra_observer.reactor.handlers import handle_high_cpu
from hydra_observer.system_state import system_state

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Register reactions
reaction_core.register("high_cpu", handle_high_cpu)

def get_system_metrics():
    """Gathers system metrics like CPU, memory, and disk usage."""
    cpu_usage = psutil.cpu_percent(interval=1)
    memory_info = psutil.virtual_memory()
    disk_info = psutil.disk_usage('/')

    metrics = {
        "cpu_usage_percent": cpu_usage,
        "memory_usage_percent": memory_info.percent,
        "disk_usage_percent": disk_info.percent,
    }
    return metrics

def update_ssv_from_metrics(metrics):
    """Updates the SSV based on system metrics."""
    cpu = metrics["cpu_usage_percent"]
    mem = metrics["memory_usage_percent"]

    # Update fatigue
    fatigue = (cpu * 0.6) + (mem * 0.4)
    system_state.update_ssv('fatigue', round(fatigue / 100, 2))

    # Update performance degradation
    degradation = 0.0
    if cpu > 90 or mem > 90:
        degradation = 0.8
    elif cpu > 75 or mem > 75:
        degradation = 0.5
    elif cpu > 50 or mem > 50:
        degradation = 0.2
    system_state.update_ssv('performance_degradation', degradation)


def run_probes(interval=60):
    """Periodically gathers and logs system metrics."""
    while True:
        try:
            metrics = get_system_metrics()
            logging.info(f"System Metrics: {metrics}")
            update_ssv_from_metrics(metrics)

            # Trigger a reaction if CPU usage is high
            if metrics["cpu_usage_percent"] > 90:
                reaction_core.trigger("high_cpu", {"cpu_percent": metrics["cpu_usage_percent"]})

        except Exception as e:
            logging.error(f"Error gathering system metrics: {e}")
        time.sleep(interval)

if __name__ == "__main__":
    logging.info("Starting system probes.")
    run_probes()
