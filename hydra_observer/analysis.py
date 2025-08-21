import logging
from hydra_observer.system_state import system_state
from collections import defaultdict
import time

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# In-memory state for analysis
command_stats = defaultdict(lambda: {'count': 0, 'total_duration': 0})
error_count = 0
total_logs = 0

def analyze_log(log_data):
    """
    Analyzes a single log entry and updates the SSV.
    """
    global total_logs, error_count
    total_logs += 1

    command = log_data.get('command')
    if command:
        # Update command frequency and duration
        stats = command_stats[command]
        stats['count'] += 1
        duration = log_data.get('duration_ms')
        if duration:
            stats['total_duration'] += duration

        # Update SSV with command frequency
        freq = {k: v['count'] for k, v in command_stats.items()}
        system_state.update_ssv('command_frequency', freq)

        # Update SSV with average latency
        avg_latency = {k: v['total_duration'] / v['count'] for k, v in command_stats.items() if v['count'] > 0}
        system_state.update_ssv('api_latency', avg_latency)

    if log_data.get('error'):
        error_count += 1

    # Update SSV with error rate
    if total_logs > 0:
        error_rate = (error_count / total_logs) * 100
        system_state.update_ssv('error_rate', error_rate)
