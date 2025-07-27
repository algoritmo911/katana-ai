import streamlit as st
from .base_agent import BaseAgent

class ZenBot(BaseAgent):
    def get_response(self, user_input):
        return "ZenBot acknowledges your presence. Breathe."

    def render_ui(self):
        st.subheader("Breathing Exercise")
        st.write("Follow the rhythm of the expanding and contracting circle.")
        # Simple animation mock
        st.empty()
