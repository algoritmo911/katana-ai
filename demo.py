import streamlit as st
from web.app import app

def run_demo():
    """
    This function runs a demo of the Katana web interface.
    """
    # To run this demo, you need to have streamlit installed.
    # You can install it by running: pip install streamlit
    # Then, you can run this demo by running: streamlit run demo.py

    st.title("Katana Web Interface Demo")

    # Add a button to start the demo
    if st.button("Start Demo"):
        # Run the main app
        app()

if __name__ == "__main__":
    run_demo()
