import streamlit as st
from .base_agent import BaseAgent

class HealerBot(BaseAgent):
    def get_response(self, user_input):
        return "HealerBot is here to offer support."

    def render_ui(self):
        st.subheader("Health Recommendations")
        st.write("- Drink more water")
        st.write("- Take a 5-minute break")
