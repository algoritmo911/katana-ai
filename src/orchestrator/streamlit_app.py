import streamlit as st
import json
from datetime import datetime
import pandas as pd

import streamlit as st
import json
from datetime import datetime
import pandas as pd

# Note: ErrorCriticality enum could be imported for type hinting or direct use if needed,
# but here we rely on string values ('high', 'medium', 'low') from the log.

def get_error_color(criticality: str) -> str:
    """
    Determines a display color based on error criticality.

    Args:
        criticality: A string representing the error's criticality
                     (e.g., "high", "medium", "low").

    Returns:
        A string representing the color (e.g., "red", "orange", "yellow").
    """
    if criticality == "high":
        return "red"
    elif criticality == "medium":
        return "orange"
    elif criticality == "low":
        return "yellow"
    return "grey" # Default for unknown or no criticality

def load_data(filepath: str) -> List[Dict[str, Any]]:
    """
    Loads and parses orchestrator log data from a JSON file.

    Args:
        filepath: The path to the JSON log file.

    Returns:
        A list of dictionaries, where each dictionary represents a round's metrics.
        Returns an empty list if the file is not found, or if there's a
        JSON decoding error or other issues.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data: List[Dict[str, Any]] = json.load(f)
        if not isinstance(data, list):
            st.error(f"Error: Data in '{filepath}' is not a valid JSON list.")
            return []
        return data
    except FileNotFoundError:
        st.error(f"Error: The file '{filepath}' was not found. Please ensure it exists.")
        return []
    except json.JSONDecodeError:
        st.error(f"Error: Could not decode JSON from '{filepath}'. Check file format.")
        return []
    except Exception as e:
        st.error(f"An unexpected error occurred while loading '{filepath}': {e}")
        return []

def display_round_data(round_data: Dict[str, Any], round_index: int) -> None:
    """
    Displays detailed information for a single processing round in the Streamlit UI.

    Uses an expander to show metrics, error summaries, task details (with color-coded
    error criticality), and any automated actions taken by the orchestrator.

    Args:
        round_data: A dictionary containing the metrics for one round.
        round_index: The (0-based) index of the round, used for display purposes.
    """
    timestamp = round_data.get('timestamp', 'N/A')
    title = f"Round {round_index + 1} ({timestamp})"

    with st.expander(title):
        # --- Round Summary Metrics ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric(label="Batch Size @ Start", value=str(round_data.get('batch_size_at_round_start', 'N/A')))
        col2.metric(label="Tasks Processed", value=str(round_data.get('tasks_processed_count', 'N/A')))
        col3.metric(label="Successful Tasks", value=str(round_data.get('successful_tasks_count', 'N/A')))
        col4.metric(label="Failed Tasks", value=str(round_data.get('failed_tasks_count', 'N/A')))

        st.metric(label="Time Taken (s)", value=f"{round_data.get('time_taken_seconds', 0):.2f}")
        st.metric(label="Success Rate", value=f"{round_data.get('success_rate', 0) * 100:.0f}%")

        # --- Error Summary by Criticality ---
        error_summary = round_data.get('error_summary_by_criticality', {})
        if error_summary:
            st.subheader("Error Summary by Criticality")
            # Dynamically create columns based on number of criticality levels present
            error_cols = st.columns(len(error_summary))
            for i, (crit, count) in enumerate(error_summary.items()):
                color = get_error_color(crit)
                # Use markdown for colored text
                error_cols[i].markdown(f"<p style='color:{color};'>{crit.capitalize()}: {count}</p>", unsafe_allow_html=True)

        # --- Individual Task Details ---
        st.subheader("Task Details")
        results_summary = round_data.get('results_summary', [])
        if not results_summary:
            st.write("No task results available for this round.")
        else:
            for task_result in results_summary:
                task_content = task_result.get('task', 'N/A')
                success = task_result.get('success', False)
                details = task_result.get('details', '')

                if success:
                    st.markdown(f"✅ **Task:** `{task_content}` - Success")
                else:
                    error_classification = task_result.get('error_classification')
                    if error_classification:
                        err_type = error_classification.get('type', 'Unknown Error')
                        err_desc = error_classification.get('description', 'No description provided.')
                        err_crit = error_classification.get('criticality', 'low') # Default to low if missing
                        color = get_error_color(err_crit)

                        st.markdown(f"❌ **Task:** `{task_content}` - <span style='color:{color}; font-weight:bold;'>Failed</span>", unsafe_allow_html=True)
                        # Use a container for better visual grouping of error details
                        with st.container():
                            st.caption(f"   Type: {err_type} | Criticality: {err_crit.upper()}")
                            st.caption(f"   Description: {err_desc}")
                            st.caption(f"   Original Details: {details}")
                    else:
                        # Fallback if error_classification is missing for a failed task
                        st.markdown(f"❌ **Task:** `{task_content}` - <span style='color:grey;font-weight:bold;'>Failed (No classification)</span>", unsafe_allow_html=True)
                        st.caption(f"   Details: {details}")

        # --- Automated Actions / Recommendations ---
        actions = round_data.get('actions_taken')
        if actions:
            st.subheader("Automated Actions / Recommendations")
            for action in actions:
                st.info(f"{action}") # Use an icon for info

def main() -> None:
    """
    Main function to set up and run the Streamlit dashboard application.

    Loads orchestrator log data, displays overall statistics, error trends,
    and detailed information for each processing round.
    """
    st.set_page_config(page_title="Katana Orchestrator Dashboard", layout="wide")
    st.title("📊 Katana Orchestrator Dashboard")

    # Configuration for the log file path
    # TODO: Consider making this configurable via an environment variable or a settings file.
    log_file_path = "orchestrator_log.json"
    orchestrator_data = load_data(log_file_path)

    if not orchestrator_data:
        st.info(f"No data loaded from '{log_file_path}'. Ensure the file exists, is not empty, and is correctly formatted. Then refresh.")
        return # Exit early if no data

    st.success(f"Successfully loaded {len(orchestrator_data)} round(s) from '{log_file_path}'.")

    # --- Overall Statistics Section ---
    st.header("Overall Statistics")
    total_tasks_processed = sum(r.get('tasks_processed_count', 0) for r in orchestrator_data)
    total_successful = sum(r.get('successful_tasks_count', 0) for r in orchestrator_data)
    # total_failed = sum(r.get('failed_tasks_count', 0) for r in orchestrator_data) # Can be derived or directly used

    stat_cols = st.columns(3)
    stat_cols[0].metric("Total Rounds Logged", len(orchestrator_data))
    stat_cols[1].metric("Total Tasks Processed", total_tasks_processed)
    if total_tasks_processed > 0:
        overall_success_rate = (total_successful / total_tasks_processed) * 100
        stat_cols[2].metric("Overall Success Rate", f"{overall_success_rate:.2f}%")
    else:
        stat_cols[2].metric("Overall Success Rate", "N/A")

    # --- Error Trends Section ---
    st.header("Error Trends Over Rounds")
    error_frequencies = []
    for i, round_d in enumerate(orchestrator_data):
        failed_count = round_d.get('failed_tasks_count', 0)
        # Summing up specific criticalities, or just using total failed tasks
        high_crit_errors = round_d.get('error_summary_by_criticality', {}).get('high', 0)
        medium_crit_errors = round_d.get('error_summary_by_criticality', {}).get('medium', 0)
        error_frequencies.append({
            'Round': i + 1, # For 1-based indexing on the chart
            'Total Failed Tasks': failed_count,
            'High Criticality Errors': high_crit_errors,
            'Medium Criticality Errors': medium_crit_errors
        })

    if error_frequencies:
        df_errors = pd.DataFrame(error_frequencies)
        # Charting total failed tasks and high criticality errors
        st.line_chart(df_errors.set_index('Round')[['Total Failed Tasks', 'High Criticality Errors', 'Medium Criticality Errors']])
    else:
        st.info("No error data available to display trends.")

    # --- Sidebar for Actions & Filters ---
    st.sidebar.header("Actions & Filters")
    show_only_rounds_with_errors = st.sidebar.checkbox("Show only rounds with errors", value=False)

    if st.sidebar.button("🔄 Refresh Data"):
        st.experimental_rerun() # Reruns the script from the top

    st.sidebar.markdown("---")
    st.sidebar.subheader("Manual Task Retry Suggestions")
    st.sidebar.info("This section identifies tasks from rounds with high or medium criticality errors, suggesting them for manual review or retry.")

    if st.sidebar.button("🔍 Identify Tasks to Retry", help="Lists tasks that failed with high/medium criticality."):
        tasks_to_retry_manually = []
        for i, round_d_retry in enumerate(orchestrator_data):
            for task_res_retry in round_d_retry.get('results_summary', []):
                if not task_res_retry.get('success'):
                    err_class_retry = task_res_retry.get('error_classification')
                    if err_class_retry and err_class_retry.get('criticality') in ['high', 'medium']:
                        tasks_to_retry_manually.append(
                            f"- Round {i+1}: Task `{task_res_retry.get('task')}` (Error: {err_class_retry.get('type')}, Criticality: {err_class_retry.get('criticality').upper()})"
                        )
        if tasks_to_retry_manually:
            st.sidebar.markdown("**Tasks suggested for manual retry:**")
            for task_info in tasks_to_retry_manually:
                st.sidebar.markdown(task_info) # Using markdown for potential formatting
        else:
            st.sidebar.info("No high/medium criticality failed tasks found to suggest for retry.")

    # --- Round Details Section ---
    st.header("Round Details")
    displayed_rounds_count = 0
    for i, round_entry_data in enumerate(orchestrator_data):
        # Apply filter: if checkbox is ticked and round has no errors, skip display
        if show_only_rounds_with_errors and round_entry_data.get('failed_tasks_count', 0) == 0:
            continue
        display_round_data(round_entry_data, i)
        displayed_rounds_count +=1

    if displayed_rounds_count == 0:
        if show_only_rounds_with_errors:
            st.info("No rounds with errors found matching the filter.")
        else:
            # This case should ideally be caught by the initial orchestrator_data check,
            # but as a fallback if data becomes empty after filtering (though unlikely here).
            st.info("No round data to display.")

if __name__ == "__main__":
    main()
