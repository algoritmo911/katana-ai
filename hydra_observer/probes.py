import logging
import psutil
import time
from hydra_observer.reactor.reaction_core import reaction_core
from hydra_observer.reactor.handlers import handle_high_cpu

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

def run_probes(interval=60):
    """Periodically gathers and logs system metrics."""
    while True:
        try:
            metrics = get_system_metrics()
            logging.info(f"System Metrics: {metrics}")

            # Trigger a reaction if CPU usage is high
            if metrics["cpu_usage_percent"] > 90:
                reaction_core.trigger("high_cpu", {"cpu_percent": metrics["cpu_usage_percent"]})

        except Exception as e:
            logging.error(f"Error gathering system metrics: {e}")
        time.sleep(interval)

if __name__ == "__main__":
    logging.info("Starting system probes.")
    run_probes()
