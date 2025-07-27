import streamlit as st
from .base_agent import BaseAgent

class PsyBot(BaseAgent):
    def get_response(self, user_input):
        # Mock EmotionEngine
        emotion = "neutral"
        if "sad" in user_input:
            emotion = "sad"
        elif "happy" in user_input:
            emotion = "happy"
        return f"PsyBot senses you are feeling {emotion}."

    def render_ui(self):
        st.subheader("Emotional State")
        st.write("Your current emotional state is: Neutral")
