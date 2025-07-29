import logging
import psutil
import time

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
        except Exception as e:
            logging.error(f"Error gathering system metrics: {e}")
        time.sleep(interval)

if __name__ == "__main__":
    logging.info("Starting system probes.")
    run_probes()
