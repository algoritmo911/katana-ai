import streamlit as st
import requests
import pandas as pd

def load_data(url: str) -> list[dict]:
    """Loads and parses the JSON data from the metrics service."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        st.error(f"Error: Could not connect to the metrics service at '{url}'. Please make sure it is running and accessible.")
        return []
    except Exception as e:
        st.error(f"An unexpected error occurred while loading the data: {e}")
        return []

def display_metrics(metrics: list[dict]):
    """Displays the metrics data in a table."""
    if not metrics:
        st.info("No metrics to display.")
        return

    df = pd.DataFrame(metrics)
    st.dataframe(df)

def main():
    """Main function to run the Streamlit application."""
    st.set_page_config(page_title="Katana Orchestrator Dashboard", layout="wide")
    st.title("Katana Orchestrator Dashboard")

    metrics_service_url = "http://localhost:8002/metrics"

    orchestrator_data = load_data(metrics_service_url)

    if orchestrator_data:
        st.success(f"Successfully loaded {len(orchestrator_data)} metric(s) from '{metrics_service_url}'.")
        display_metrics(orchestrator_data)
    else:
        st.info("No data to display. Ensure the metrics service is running and collecting data.")

if __name__ == "__main__":
    main()
