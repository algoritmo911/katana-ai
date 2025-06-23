import streamlit as st
import json
from pathlib import Path

LOG_FILE_NAME = "orchestrator_log.json"
LOG_FILE_PATH = Path(LOG_FILE_NAME) # Assumes log file is in the same directory as where streamlit is run

def load_log_data(log_file_path: Path) -> list[dict] | None:
    """
    Loads log data from a JSONL file (JSON objects separated by newlines).
    Returns a list of dictionaries (log entries) or None if an error occurs.
    Entries are sorted from newest to oldest.
    """
    if not log_file_path.exists():
        st.warning(f"{LOG_FILE_NAME} not found at {log_file_path.resolve()}")
        return None

    log_entries = []
    try:
        with open(log_file_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        log_entries.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        st.error(f"Error decoding JSON from a line in {LOG_FILE_NAME}: {e}\nProblematic line: '{line}'")
                        # Continue processing other lines if possible, or return None to stop
                        # For now, let's be strict and stop if any line is bad.
                        return None
        return sorted(log_entries, key=lambda x: x.get("timestamp", 0), reverse=True)
    except Exception as e:
        st.error(f"Failed to read or process {LOG_FILE_NAME}: {e}")
        return None

def main():
    st.set_page_config(layout="wide", page_title="Orchestrator Monitor", initial_sidebar_state="collapsed")
    # Applying dark theme through config is tricky, Streamlit prefers theme setting in .streamlit/config.toml
    # However, we can use custom CSS if needed, or rely on user's OS/browser preference if supported.
    # For now, we'll let Streamlit handle the theme. The prompt mentioned "dark theme" as a preference.
    # Streamlit's default "auto" theme should respect system settings.

    st.title("⚙️ Orchestrator Monitor")

    log_data = load_log_data(LOG_FILE_PATH)

    if log_data is None:
        st.info("No log data to display currently. Waiting for logs...")
        return

    if not log_data:
        st.info(f"{LOG_FILE_NAME} is empty or contains no valid log entries.")
        return

    st.metric("Total Rounds Logged", len(log_data))

    st.markdown("---")

    for i, entry in enumerate(log_data):
        round_num = entry.get("round", "N/A")
        timestamp = entry.get("timestamp", "N/A")

        # Construct expander title
        expander_title = f"Round: {round_num}"
        if timestamp != "N/A":
            try:
                # Attempt to format timestamp if it's a number
                from datetime import datetime
                ts_datetime = datetime.fromtimestamp(float(timestamp))
                expander_title += f"  |  Timestamp: {ts_datetime.strftime('%Y-%m-%d %H:%M:%S')}"
            except ValueError:
                expander_title += f"  |  Timestamp: {timestamp}" # Keep as is if not a standard timestamp
        else:
            expander_title += f"  |  Timestamp: {timestamp}"


        with st.expander(expander_title, expanded=(i==0)): # Expand the first (newest) entry by default
            batch_size = entry.get("batch_size", "N/A")
            avg_time = entry.get("avg_time_per_task_seconds")
            errors = entry.get("error_types_in_batch", [])

            col1, col2 = st.columns(2)
            with col1:
                st.info(f"**Batch Size:** `{batch_size}`")
            with col2:
                if avg_time is not None:
                    st.info(f"**Avg. Time/Task:** `{avg_time:.2f}s`")
                else:
                    st.info("**Avg. Time/Task:** `N/A`")

            if errors:
                st.error("**Errors in Batch:**")
                # st.json(errors) # Option 1: display as JSON
                for err_idx, error_detail in enumerate(errors):
                    if isinstance(error_detail, dict):
                        st.text(f"  - Type: {error_detail.get('type', 'Unknown')}, Count: {error_detail.get('count', 'N/A')}")
                    else:
                        st.text(f"  - {error_detail}")

            else:
                st.success("**No errors reported in this batch.**")

            # Display raw entry for more details if needed
            with st.popover("Raw Log Entry"):
                st.json(entry)


if __name__ == "__main__":
    main()
