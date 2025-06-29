import streamlit as st

# This will be moved to katana.core.brain eventually
def katana_respond(user_input: str) -> str:
    return f"Я получила: {user_input}. Ответ будет… скоро!"

st.title("💬 Katana Chat Interface")
user_input = st.text_input("Твой приказ:")

if user_input:
    with st.spinner("Katana обрабатывает..."):
        # Временный ответ — позже связать с настоящим ядром
        response = katana_respond(user_input)
        st.markdown(f"**Katana:** {response}")
