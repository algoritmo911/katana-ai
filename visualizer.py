import streamlit as st
import pandas as pd
import json
import sys
import graphviz

st.set_page_config(layout="wide")

st.title("Katana Command Visualizer")

# --- Data Loading and Parsing ---
@st.cache_data
def load_data(log_file):
    """Loads command logs from a file and parses them into a DataFrame."""
    lines = []
    with open(log_file, 'r') as f:
        for line in f:
            try:
                lines.append(json.loads(line))
            except json.JSONDecodeError:
                # Ignore lines that are not valid JSON
                pass
    df = pd.DataFrame(lines)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

# --- UI Components ---
def display_command_table(df):
    """Displays the main command table."""
    st.header("Command History")
    st.dataframe(df[['timestamp', 'command', 'user_id', 'duration_ms', 'error']], use_container_width=True)

def display_command_details(command):
    """Displays the details of a selected command."""
    st.header("Command Details")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Command", command['command'])
        st.metric("Timestamp", str(command['timestamp']))
        st.metric("User ID", command['user_id'])
        st.metric("Duration (ms)", f"{command['duration_ms']:.2f}")
    with col2:
        st.subheader("Arguments")
        st.json(command['args'])
        st.subheader("Keyword Arguments")
        st.json(command['kwargs'])
    st.subheader("Result")
    st.json(command['result'])
    if command['error']:
        st.subheader("Error")
        st.error(command['error'])

def display_execution_graph(command, df):
    """Displays the execution graph for a selected command."""
    st.header("Execution Graph")
    dot = graphviz.Digraph(comment='Command Execution')
    dot.attr('node', shape='box', style='rounded')

    # Add the selected command to the graph
    node_label = f"{command['command']}\nDuration: {command['duration_ms']:.2f}ms"
    node_color = "red" if command['error'] else "green"
    dot.node(str(command.name), node_label, color=node_color)

    # For now, we'll just show the single node.
    # Later, we'll add logic to trace the execution path.

    st.graphviz_chart(dot)

# --- Main Application Logic ---
if __name__ == "__main__":
    if sys.stdin.isatty():
        # If running in a TTY, use the dummy log file
        log_file = "commands.log"
        try:
            df = load_data(log_file)
        except FileNotFoundError:
            st.warning(f"Log file not found: {log_file}")
            st.info("Please run the bot to generate logs.")
            df = pd.DataFrame()
    else:
        # If not in a TTY, read from stdin
        df = load_data(sys.stdin)

    if not df.empty:
        display_command_table(df)
        selected_command_index = st.selectbox("Select a command to inspect", df.index)
        if selected_command_index is not None:
            selected_command = df.loc[selected_command_index]
            display_command_details(selected_command)
            display_execution_graph(selected_command, df)
