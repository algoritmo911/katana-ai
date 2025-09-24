import os
import streamlit as st
from supabase import create_client, Client
from dotenv import load_dotenv
import pandas as pd

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# --- Initialize Supabase client ---
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Error connecting to Supabase: {e}")
    st.stop()

# --- Streamlit App ---
st.set_page_config(page_title="Swarm Dispatcher Dashboard", layout="wide")

st.title("🐝 Swarm Dispatcher Task Dashboard")

def fetch_tasks():
    """Fetches all tasks from the Supabase 'tasks' table."""
    try:
        response = supabase.table('tasks').select("id, description, status, coder_id, repo_url").order('id', desc=True).execute()
        if response.data:
            # Convert to pandas DataFrame for better display
            df = pd.DataFrame(response.data)
            return df
        else:
            return pd.DataFrame() # Return empty dataframe if no tasks
    except Exception as e:
        st.error(f"An error occurred while fetching tasks: {e}")
        return None

# --- Main Page ---
st.header("All Tasks")

# Placeholder for the dataframe
data_placeholder = st.empty()

# Fetch and display data
tasks_df = fetch_tasks()

if tasks_df is not None:
    if not tasks_df.empty:
        # Reorder columns for better readability
        display_columns = ['id', 'description', 'status', 'coder_id', 'repo_url']
        tasks_df = tasks_df[display_columns]
        data_placeholder.dataframe(tasks_df, use_container_width=True)
    else:
        st.info("No tasks found in the database.")
else:
    st.warning("Could not load tasks.")

# Add a button to manually refresh the data
if st.button('Refresh Data'):
    st.rerun()