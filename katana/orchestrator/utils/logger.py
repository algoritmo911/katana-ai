import logging
import json

def setup_logger(name, log_file, level=logging.INFO):
    """
    Sets up a logger.
    """
    handler = logging.FileHandler(log_file)
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger

class JsonTrace:
    def __init__(self, trace_file):
        self.trace_file = trace_file
        self.trace = []

    def add_step_trace(self, step_id, status, start_time, end_time, logs):
        self.trace.append({
            "step": step_id,
            "status": status,
            "start": start_time,
            "end": end_time,
            "logs": logs,
        })

    def save(self):
        with open(self.trace_file, "w") as f:
            json.dump(self.trace, f, indent=4)
