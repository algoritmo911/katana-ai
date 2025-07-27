print("Starting web/app.py")
import streamlit as st
import sys
import os

print("Imports successful")

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print("Path updated")

from web.utils.router import AgentRouter
from web.utils.session import UserSession
from web.agents.psy_bot import PsyBot
from web.agents.zen_bot import ZenBot
from web.agents.coach_bot import CoachBot
from web.agents.healer_bot import HealerBot

print("Agent imports successful")

# Page configuration
st.set_page_config(page_title="Katana Interface", page_icon="⚔️", layout="centered")

# Custom CSS for theming
st.markdown(f"""
    <style>
        body {{
            background-image: url("https://www.google.com/url?sa=i&url=https%3A%2F%2Fwww.pexels.com%2Fsearch%2Fdark%2F&psig=AOvVaw1g-p-Z-x3Ea-j3Y-jQ_7aU&ust=1722174092001000&source=images&cd=vfe&ved=0CBEQjRxqFwoTCIjR-f-jv4cDFQAAAAAdAAAAABAE");
            background-size: cover;
            background-repeat: no-repeat;
            background-attachment: fixed;
            background-color: {"#FFFFFF" if theme == "Light" else "#121212"};
            color: {"#000000" if theme == "Light" else "#FFFFFF"};
        }}
        .stApp {{
            background-color: {"#FFFFFF" if theme == "Light" else "#121212"};
        }}
        .stTextInput > div > div > input, .stTextArea > div > div > textarea {{
            background-color: {"#F0F2F6" if theme == "Light" else "#333333"} !important;
            color: {"#000000" if theme == "Light" else "#FFFFFF"} !important;
            border: 1px solid {"#E0E0E0" if theme == "Light" else "#4f4f4f"} !important;
        }}
        .stButton > button {{
            background-color: {"#F0F2F6" if theme == "Light" else "#4a4a4a"};
            color: {"#000000" if theme == "Light" else "#FFFFFF"};
            border: 1px solid {"#E0E0E0" if theme == "Light" else "#5f5f5f"};
        }}
        [data-testid="chat-message-container"] {{
            background-color: {"#F0F2F6" if theme == "Light" else "#2a2a2a"};
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 10px;
            border: 1px solid {"#E0E0E0" if theme == "Light" else "#383838"};
        }}
    </style>
""", unsafe_allow_html=True)

st.title("🤖 Интерфейс чата Katana")
st.markdown("Добро пожаловать в интерфейс Katana!")
print("[DEBUG] streamlit_app.py: UI elements (title, markdown) rendered.")

# Mock authentication
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("Login to Katana")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username and password:
            st.session_state.authenticated = True
            st.session_state.user_session = UserSession()
            st.session_state.agent_router = AgentRouter()
            st.session_state.agent_router.register_agent("PsyBot", PsyBot())
            st.session_state.agent_router.register_agent("ZenBot", ZenBot())
            st.session_state.agent_router.register_agent("CoachBot", CoachBot())
            st.session_state.agent_router.register_agent("HealerBot", HealerBot())
            st.experimental_rerun()
else:
    # App content goes here
    # ...

    # Initialize chat history
    if "history" not in st.session_state:
        st.session_state.history = []

    # Sidebar for agent selection and theme toggle
    st.sidebar.image("https://www.google.com/url?sa=i&url=https%3A%2F%2Fwww.freepik.com%2Ffree-photos-vectors%2Fkatana-logo&psig=AOvVaw1g-p-Z-x3Ea-j3Y-jQ_7aU&ust=1722174092001000&source=images&cd=vfe&ved=0CBEQjRxqFwoTCIjR-f-jv4cDFQAAAAAdAAAAABAE", width=100)
    st.sidebar.title("Controls")
    theme = st.sidebar.selectbox("Choose a theme:", ["Dark", "Light"])
    agent_name = st.sidebar.selectbox(
        "Choose your agent:",
        st.session_state.agent_router.list_agents()
    )
    st.session_state.active_agent = st.session_state.agent_router.get_agent(agent_name)

    def get_katana_response_from_backend(user_query: str) -> str:
        """
        Gets a response from the selected Katana agent.
        """
        if "active_agent" in st.session_state and hasattr(st.session_state.active_agent, "get_response"):
            return st.session_state.active_agent.get_response(user_query)
        return "No active agent selected or agent does not have a get_response method."

    # Render the active agent's UI
    if "active_agent" in st.session_state:
        st.session_state.active_agent.render_ui()

    # Chat input and history
    user_input = st.chat_input("Your message to Katana:")

    if user_input:
        st.session_state.history.append({"role": "user", "content": user_input})
        bot_response_content = get_katana_response_from_backend(user_input)
        st.session_state.history.append({"role": "assistant", "content": bot_response_content})

    # Display chat history
    for message in st.session_state.history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
