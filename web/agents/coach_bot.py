import streamlit as st
from .base_agent import BaseAgent

class CoachBot(BaseAgent):
    def get_response(self, user_input):
        return "CoachBot is ready to help you with your goals."

    def render_ui(self):
        st.subheader("Goal Planner")
        goal = st.text_input("What is your goal?")
        if goal:
            st.write(f"Your goal is set: {goal}")
