import streamlit as st
import sys
import os
import asyncio

# Add project root to sys.path to allow importing 'bot'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

try:
    from bot import get_core_response
    BOT_CORE_AVAILABLE = True
except ImportError as e:
    BOT_CORE_AVAILABLE = False
    st.error(f"Failed to import Katana bot core: {e}. Please ensure bot.py is available.")

def get_bot_response(user_input: str) -> str:
    """
    Calls the asynchronous bot core function from a synchronous context.
    """
    if not BOT_CORE_AVAILABLE:
        return "Error: Bot core is not available."
    try:
        # Streamlit runs in a sync context. To call our async function,
        # we need to run it in a new asyncio event loop.
        response = asyncio.run(get_core_response(user_input))
        return response
    except Exception as e:
        st.error(f"Error when calling bot core: {e}")
        return f"An error occurred while processing your request: {e}"

def main():
    st.title("Katana AI Chat")

    if not BOT_CORE_AVAILABLE:
        st.warning("Katana bot core is not loaded. Responses are unavailable.")

    # Initialize chat history in session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display chat history
    for i, (user_msg, bot_msg) in enumerate(st.session_state.chat_history):
        st.chat_message("user", key=f"user_{i}").write(user_msg)
        st.chat_message("assistant", key=f"bot_{i}").write(bot_msg)

    # User input
    if user_input := st.chat_input("Ask Katana..."):
        st.session_state.chat_history.append((user_input, "…thinking…"))
        st.rerun()

    # Process the latest message
    if st.session_state.chat_history:
        last_user_msg, last_bot_msg = st.session_state.chat_history[-1]
        if last_bot_msg == "…thinking…":
            response = get_bot_response(last_user_msg)
            st.session_state.chat_history[-1] = (last_user_msg, response)
            st.rerun()

if __name__ == "__main__":
    main()
