import streamlit as st
import sys
import os

# --- Начало блока для корректного импорта katana ---
# Добавляем корень проекта в sys.path, чтобы можно было импортировать 
katana.
# Это важно, так как streamlit_app.py находится в корне, а katana - это 
директория.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 
'.')))
print(f"[DEBUG] sys.path (streamlit_app.py): {sys.path}")
SELF_EVOLVER_AVAILABLE = False # По умолчанию считаем недоступным
try:
    from katana.self_evolve import SelfEvolver
    SELF_EVOLVER_AVAILABLE = True
    print("[DEBUG] SelfEvolver imported successfully.")
except ImportError as ie:
    print(f"[ERROR] Failed to import SelfEvolver: {ie}. Check if 
katana/self_evolve.py exists and is correct.")
except Exception as e:
    print(f"[ERROR] An unexpected error occurred during SelfEvolver 
import: {e}")
# --- Конец блока для корректного импорта katana ---

# Конфигурация страницы
st.set_page_config(page_title="Katana Interface", page_icon="⚔️", 
layout="centered")

# Установка кастомного CSS для тёмного фона и светлого текста
st.markdown(
    """
    <style>
    /* Основной фон приложения */
    .stApp {
        background-color: #121212;
    }
    /* Для старых версий Streamlit или если .stApp не срабатывает */
    .reportview-container .main {
        background-color: #121212;
        color: #e0e0e0;
    }
    body > #root > div:nth-child(1) > div:nth-child(1) > div > div {
        background-color: #121212; /* Более специфичный селектор */
    }

    /* Цвет текста по умолчанию */
    body, .stMarkdown, p, li, label {
        color: #e0e0e0;
    }

    /* Заголовки */
    h1, h2, h3, h4, h5, h6 {
        color: #f5f5f5; /* Чуть ярче для заголовков */
    }

    /* Поле ввода текста */
    .stTextInput > div > div > input, .stTextArea > div > div > textarea {
        background-color: #333333 !important;
        color: #e0e0e0 !important;
        border: 1px solid #4f4f4f !important;
    }
    
    /* Placeholder в текстовом поле */
    .stTextInput input::placeholder {
        color: #a0a0a0 !important;
    }

    /* Кнопки (если будут) */
    .stButton > button {
        background-color: #4a4a4a;
        color: #e0e0e0;
        border: 1px solid #5f5f5f;
    }
    .stButton > button:hover {
        background-color: #5a5a5a;
        border-color: #6f6f6f;
    }

    /* Сообщения чата */
    [data-testid="chat-message-container"] {
        background-color: #2a2a2a;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 10px;
        border: 1px solid #383838;
    }
    [data-testid="stChatMessageContent"] p, 
[data-testid="stChatMessageContent"] div {
        color: #e0e0e0 !important; /* Важно для переопределения */
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🤖 Интерфейс чата Katana")
st.markdown("Добро пожаловать в интерфейс Katana!")
print("[DEBUG] streamlit_app.py: UI elements (title, markdown) rendered.")

# Инициализация истории и экземпляра Katana в session_state
if "history" not in st.session_state:
    st.session_state.history = []
    print("[DEBUG] Chat history initialized in session_state.")

if SELF_EVOLVER_AVAILABLE and 'katana_instance' not in st.session_state:
    try:
        st.session_state.katana_instance = SelfEvolver()
        print("[DEBUG] SelfEvolver instance created and cached in 
session_state.")
    except Exception as e:
        print(f"[ERROR] Failed to create SelfEvolver instance: {e}")
        # Не перезаписываем SELF_EVOLVER_AVAILABLE здесь, так как он уже 
False из блока импорта, если была ошибка
        st.error(f"Ошибка инициализации KatanaAgent: {e}")


def get_katana_response_from_backend(user_query: str) -> str:
    """
    Получает ответ от KatanaAgent (SelfEvolver).
    """
    print(f"[DEBUG] get_katana_response_from_backend called with query: 
'{user_query}'")
    if not SELF_EVOLVER_AVAILABLE:
        error_msg = "⚠️ KatanaAgent (SelfEvolver) не импортирован. 
Проверьте лог на ошибки импорта."
        print(f"[ERROR] {error_msg}")
        return error_msg
    if 'katana_instance' not in st.session_state:
        error_msg = "⚠️ Экземпляр KatanaAgent (SelfEvolver) не был создан. 
Проверьте лог на ошибки инициализации."
        print(f"[ERROR] {error_msg}")
        return error_msg
    
    try:
        katana = st.session_state.katana_instance
        response = katana.generate_patch(user_query)
        print(f"[DEBUG] SelfEvolver.generate_patch returned: 
'{response}'")
        if response is None:
            return "Катана получила ваш запрос, но не сформировала ответ 
(получен None)."
        return response
    except Exception as e:
        error_msg = f"⚠️ Ошибка при взаимодействии с KatanaAgent: {e}"
        print(f"[ERROR] Exception in get_katana_response_from_backend: 
{error_msg}", exc_info=True)
        return error_msg

# Логика обработки ввода и отображения
# Используем st.chat_input для более "чатового" вида и автоматической 
очистки поля
user_input = st.chat_input("Ваш вопрос к Katana:")
print(f"[DEBUG] streamlit_app.py: Checked for user_input from chat_input. 
Value: '{user_input if user_input else 'None'}'")

if user_input:
    print(f"[DEBUG] User input received: '{user_input}'")
    st.session_state.history.append({"role": "user", "content": 
user_input})
    
    print("[DEBUG] Calling Katana backend for response...")
    bot_response_content = get_katana_response_from_backend(user_input)
    st.session_state.history.append({"role": "assistant", "content": 
bot_response_content})
    print(f"[DEBUG] Bot response added to history: 
'{bot_response_content}'")
    # st.chat_input автоматически вызывает rerun, поэтому история 
обновится

# Отображение истории чата
if st.session_state.history:
    # print(f"[DEBUG] Displaying chat history. Items: 
{len(st.session_state.history)}") # Закомментировано, чтобы не спамить лог 
при каждом rerun
    for message_entry in st.session_state.history:
        role = message_entry.get("role")
        content = message_entry.get("content")
        if role and content is not None: # Проверка, что content не None
            with st.chat_message(role, avatar="⚔️" if role == "assistant" 
else None):
                st.markdown(str(content)) # Убедимся, что content это 
строка
else:
    print("[DEBUG] Chat history is empty. Nothing to display yet.")

if not SELF_EVOLVER_AVAILABLE:
    st.warning("Внимание: KatanaAgent (SelfEvolver) не удалось загрузить. 
Ответы будут ограничены или не будут работать. Проверьте консоль сервера 
на наличие ошибок импорта.")

print(f"[DEBUG] streamlit_app.py: Script execution finished for this run. 
User input was: '{user_input if user_input else 'None'}'")
