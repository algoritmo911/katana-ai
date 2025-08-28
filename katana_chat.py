import streamlit as st
import requests
import json

# --- Configuration ---
BACKEND_URL = "http://127.0.0.1:8000/api/v1/command"

# --- UI Setup ---
st.set_page_config(
    page_title="Katana: Chimera Protocol",
    page_icon="🗡️"
)

st.title("Протокол 'Химера'")
st.caption("Слой 1: Разумный Слушатель")

# --- Session State ---
# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# --- Main Interaction Logic ---
if prompt := st.chat_input("Введите команду..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        try:
            # Send command to the backend
            response = requests.post(BACKEND_URL, json={"text": prompt})
            response.raise_for_status()  # Raise an exception for bad status codes

            response_data = response.json()
            full_response = response_data.get("response", "Error: No response field in JSON")

        except requests.exceptions.RequestException as e:
            full_response = f"**Ошибка подключения к бэкенду:**\n\n```\n{e}\n```\n\nУбедитесь, что бэкенд запущен: `uvicorn katana_single_app.main:app --host 0.0.0.0 --port 8000`"
        except json.JSONDecodeError:
            full_response = "Ошибка: Не удалось декодировать JSON ответ от бэкенда."
        except Exception as e:
            full_response = f"Произошла непредвиденная ошибка: {e}"

        message_placeholder.markdown(full_response)

    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": full_response})
