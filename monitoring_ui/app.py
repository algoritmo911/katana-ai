import streamlit as st
import pandas as pd
import json
import time
from datetime import datetime

# Path to the log file - assuming it's in the parent directory relative to this script
LOG_FILE_PATH = "../orchestrator_log.json"

st.set_page_config(layout="wide")

st.title("Orchestrator Monitoring Dashboard")

# Placeholder for data
data_placeholder = st.empty()

def load_log_data(log_file: str) -> list:
    """Loads log data from the JSON file."""
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            log_entries = json.load(f)
        if not isinstance(log_entries, list):
            st.error(f"Log file {log_file} does not contain a JSON list. Displaying empty data.")
            return []
        return log_entries
    except FileNotFoundError:
        st.warning(f"Log file {log_file} not found. Displaying empty data.")
        return []
    except json.JSONDecodeError:
        st.error(f"Error decoding JSON from {log_file}. File might be corrupted or empty. Displaying empty data.")
        return []
    except Exception as e:
        st.error(f"An unexpected error occurred while loading the log file: {e}")
        return []

def display_metrics(log_entries: list):
    """Displays key metrics and charts based on log entries."""
    if not log_entries:
        st.info("No data to display. Waiting for logs...")
        return

    df = pd.DataFrame(log_entries)

    # Convert timestamp to datetime
    df['timestamp_dt'] = pd.to_datetime(df['timestamp'])

    # Overall Stats
    st.header("Overall Statistics")
    total_tasks_processed_in_batches = df['tasks_processed_in_batch'].sum()
    total_successful_tasks = df['successful_tasks_count'].sum()
    total_failed_tasks_in_batches = df['failed_tasks_count'].sum() # Failed in batch, not necessarily given up

    overall_success_rate = (total_successful_tasks / total_tasks_processed_in_batches * 100) if total_tasks_processed_in_batches > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Tasks Processed (in Batches)", f"{total_tasks_processed_in_batches:,}")
    col2.metric("Total Successful Tasks", f"{total_successful_tasks:,}")
    col3.metric("Overall Success Rate", f"{overall_success_rate:.2f}%")

    # Note: Tasks pending in queue and retry status are not directly in this log.
    # That information is available from orchestrator's get_status() endpoint.
    # This dashboard only visualizes the historical log file.

    st.header("Performance Over Time")

    # Batch Success Rate Over Time
    if not df.empty and 'timestamp_dt' in df.columns and 'success_rate_in_batch' in df.columns:
        st.subheader("Batch Success Rate (%) Over Time")
        # Ensure 'success_rate_in_batch' is numeric, coercing errors
        df['success_rate_in_batch_numeric'] = pd.to_numeric(df['success_rate_in_batch'] * 100, errors='coerce')
        st.line_chart(df.set_index('timestamp_dt')['success_rate_in_batch_numeric'])
    else:
        st.info("Not enough data or missing columns for 'Batch Success Rate Over Time' chart.")

    # Avg Time Per Task Over Time
    if not df.empty and 'timestamp_dt' in df.columns and 'avg_time_per_task_seconds' in df.columns:
        st.subheader("Average Time Per Task (seconds) Over Time")
        df['avg_time_per_task_seconds_numeric'] = pd.to_numeric(df['avg_time_per_task_seconds'], errors='coerce')
        st.line_chart(df.set_index('timestamp_dt')['avg_time_per_task_seconds_numeric'])
    else:
        st.info("Not enough data or missing columns for 'Average Time Per Task Over Time' chart.")


    # Error Types Distribution (from last N rounds if too many)
    st.header("Error Analysis")
    all_error_types = {}
    for errors in df['error_types_in_batch'].dropna(): # dropna in case of missing data
        if isinstance(errors, dict):
            for error_type, count in errors.items():
                all_error_types[error_type] = all_error_types.get(error_type, 0) + count

    if all_error_types:
        st.subheader("Distribution of Error Types (Across All Batches)")
        error_df = pd.DataFrame(list(all_error_types.items()), columns=['Error Type', 'Count']).set_index('Error Type')
        st.bar_chart(error_df)
    else:
        st.info("No error type data available.")


    st.header("Recent Batch Details")
    # Display relevant columns from the log, newest first
    if not df.empty:
        display_cols = [
            'timestamp', 'tasks_processed_in_batch', 'successful_tasks_count',
            'failed_tasks_count', 'success_rate_in_batch', 'time_taken_seconds',
            'avg_time_per_task_seconds', 'error_types_in_batch'
        ]
        # Filter out columns that might not exist if the log is from an older version
        existing_display_cols = [col for col in display_cols if col in df.columns]
        st.dataframe(df.sort_values(by='timestamp_dt', ascending=False)[existing_display_cols].head(20))
    else:
        st.info("No batch details to display.")

# Auto-refresh setup
refresh_interval = st.sidebar.slider("Refresh interval (seconds)", 5, 60, 10)
st.sidebar.info(f"Dashboard will refresh every {refresh_interval} seconds.")

# Main loop for auto-refresh
while True:
    log_data = load_log_data(LOG_FILE_PATH)
    with data_placeholder.container(): # Update content within the placeholder
        display_metrics(log_data)
    time.sleep(refresh_interval)
    # No st.experimental_rerun() needed here as Streamlit's script execution model
    # combined with the while True loop and time.sleep effectively creates a refresh.
    # For more complex state management or interactions, st.experimental_rerun might be useful.
    # However, for just reloading data, this is simpler.
    # The page will re-run from top after sleep.
    # To make this truly effective without full page reload flicker for users,
    # one might use session_state to preserve parts of the UI or data if not changed.
    # For this simple dashboard, a full re-render on interval is acceptable.
    st.rerun() # Ensures Streamlit re-runs the script to refresh data
