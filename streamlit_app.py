import streamlit as st
import sys
import os

# Добавляем корень проекта в sys.path, чтобы можно было импортировать katana
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

try:
    from katana.self_evolve import SelfEvolver
    katana_agent_available = True
    # Инициализируем SelfEvolver один раз, чтобы не создавать его при каждом запросе
    # st.cache_resource можно использовать для более "правильного" управления ресурсами в Streamlit
    if 'katana_evolver' not in st.session_state:
        st.session_state.katana_evolver = SelfEvolver()
except ImportError as e:
    katana_agent_available = False
    st.error(f"Ошибка импорта KatanaAgent (SelfEvolver): {e}. Убедитесь, что модуль katana доступен.")
    # Определим st.session_state.katana_evolver как None, чтобы избежать ошибок далее
    st.session_state.katana_evolver = None


# Функция для получения ответа от KatanaAgent
def get_katana_response(user_input: str) -> str:
    if not katana_agent_available or st.session_state.katana_evolver is None:
        return "Ошибка: KatanaAgent недоступен."
    try:
        # Пока что SelfEvolver.generate_patch синхронный.
        # Если бы он был асинхронным, или требовал длительного времени,
        # нужно было бы использовать asyncio.to_thread или другие подходы.
        response = st.session_state.katana_evolver.generate_patch(user_input)
        return response
    except Exception as e:
        st.error(f"Ошибка при вызове KatanaAgent: {e}")
        return f"Произошла ошибка при обработке вашего запроса: {e}"

def main():
    st.title("Katana Chat UI")
    if not katana_agent_available:
        st.warning("KatanaAgent не загружен. Ответы будут ограничены.")

    # Инициализация истории чата в сессии
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Вывод истории сообщений
    for i, (user_msg, bot_msg) in enumerate(st.session_state.chat_history):
        st.chat_message("user", key=f"user_{i}").write(user_msg)
        st.chat_message("assistant", key=f"bot_{i}").write(bot_msg)

    # Ввод сообщения пользователя
    if user_input := st.chat_input("Напиши сообщение Katana..."):
        st.session_state.chat_history.append((user_input, "…обрабатываю…"))
        st.experimental_rerun()

    # Обработка последнего сообщения
    if st.session_state.chat_history:
        last_user_msg, last_bot_msg = st.session_state.chat_history[-1]
        if last_bot_msg == "…обрабатываю…":
            response = get_katana_response(last_user_msg)
            st.session_state.chat_history[-1] = (last_user_msg, response)
            st.experimental_rerun()

if __name__ == "__main__":
    main()
