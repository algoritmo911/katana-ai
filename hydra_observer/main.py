import threading
import logging
from hydra_observer import observer, probes, watchers

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """Starts all the components of the Hydra Observer."""
    logging.info("Initializing Katana Hydra Observer")

    # Create threads for each component
    observer_thread = threading.Thread(target=observer.main, name="ObserverThread")
    probes_thread = threading.Thread(target=probes.run_probes, name="ProbesThread")
    watchers_thread = threading.Thread(target=watchers.watch_for_critical_events, name="WatchersThread")

    # Start all threads
    observer_thread.start()
    probes_thread.start()
    watchers_thread.start()

    logging.info("All Hydra Observer components started.")

    # Keep the main thread alive
    observer_thread.join()
    probes_thread.join()
    watchers_thread.join()

    logging.info("Katana Hydra Observer has shut down.")

if __name__ == "__main__":
    main()
