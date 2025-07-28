import streamlit as st
import json
from datetime import datetime

def load_data(filepath: str) -> list[dict]:
    """Loads and parses the JSON log file."""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        st.error(f"Error: The file '{filepath}' was not found. Please make sure it exists in the correct location.")
        return []
    except json.JSONDecodeError:
        st.error(f"Error: Could not decode JSON from '{filepath}'. Please check the file format.")
        return []
    except Exception as e:
        st.error(f"An unexpected error occurred while loading the data: {e}")
        return []

def display_round_data(round_data: dict):
    """Displays the data for a single round using st.expander."""
    round_number = round_data.get('round', 'N/A')
    with st.expander(f"Round {round_number}"):
        st.metric(label="Round Number", value=str(round_number))
        st.metric(label="Batch Size", value=str(round_data.get('batch_size', 'N/A')))
        st.metric(label="Avg. Time per Task (s)", value=f"{round_data.get('avg_time_per_task_seconds', 'N/A'):.2f}" if isinstance(round_data.get('avg_time_per_task_seconds'), (int, float)) else 'N/A')

        error_types = round_data.get('error_types_in_batch', [])
        if isinstance(error_types, dict): # Assuming errors might be a dict {type: count}
            st.write("Error Types in Batch:")
            for error_type, count in error_types.items():
                st.write(f"- {error_type}: {count}")
        elif isinstance(error_types, list) and error_types: # Assuming errors might be a list of strings
            st.write("Error Types in Batch:")
            for error_type in error_types:
                st.write(f"- {error_type}")
        elif not error_types:
            st.write("Error Types in Batch: None")
        else:
            st.write(f"Error Types in Batch: {error_types}")


        start_time_str = round_data.get('start_time')
        end_time_str = round_data.get('end_time')

        st.write(f"Start Time: {start_time_str if start_time_str else 'N/A'}")
        st.write(f"End Time: {end_time_str if end_time_str else 'N/A'}")

        if start_time_str and end_time_str:
            try:
                # Attempt to parse ISO format datetime strings
                start_time_dt = datetime.fromisoformat(start_time_str)
                end_time_dt = datetime.fromisoformat(end_time_str)
                duration = end_time_dt - start_time_dt
                st.metric(label="Duration", value=str(duration))
            except ValueError:
                st.warning("Could not parse timestamps to calculate duration. Ensure they are in ISO format (YYYY-MM-DDTHH:MM:SS.ffffff).")
            except Exception as e:
                st.error(f"Error calculating duration: {e}")
        else:
            st.write("Duration: N/A (Missing start or end time)")

def main():
    """Main function to run the Streamlit application."""
    st.set_page_config(page_title="Katana Orchestrator Dashboard", layout="wide")
    st.title("Katana Orchestrator Dashboard")

    # Assuming orchestrator_log.json is in the root directory relative to where streamlit is run
    # or in the same directory as the script if run directly.
    # For robustness, one might want to make this path configurable.
    log_file_path = "orchestrator_log.json"

    orchestrator_data = load_data(log_file_path)

    if orchestrator_data:
        st.success(f"Successfully loaded {len(orchestrator_data)} round(s) from '{log_file_path}'.")
        for round_entry in orchestrator_data:
            display_round_data(round_entry)
    else:
        st.info("No data to display. Ensure 'orchestrator_log.json' exists and is correctly formatted.")

if __name__ == "__main__":
    main()
