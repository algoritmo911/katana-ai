import streamlit as st
import sys
import os

# Добавляем корень проекта в sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from katana.health.check import check_openai, check_supabase, check_n8n
    health_checks_available = True
except ImportError as e:
    st.error(f"Не удалось импортировать функции проверки: {e}")
    health_checks_available = False

def render_status(service_name, status, color, message):
    """Отображает статус сервиса в красивом виде."""
    st.markdown(
        f"""
        <div style="
            border: 1px solid #e6e6e6;
            border-left: 5px solid {color};
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 10px;
        ">
            <h4 style="margin: 0; padding: 0;">{service_name}</h4>
            <p style="margin: 5px 0 0 0; color: {color}; font-weight: bold;">{status}</p>
            <small style="margin: 0; padding: 0; color: #888;">{message}</small>
        </div>
        """,
        unsafe_allow_html=True
    )

def health_dashboard_page():
    st.title("Дашборд Здоровья Системы")
    st.markdown("Состояние ключевых подсистем в реальном времени.")

    if not health_checks_available:
        st.error("Модуль проверки здоровья недоступен. Невозможно отобразить статусы.")
        return

    # Создаем три колонки для более компактного отображения
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("OpenAI")
        status, color, msg = check_openai()
        render_status("OpenAI API", status, color, msg)

    with col2:
        st.subheader("Supabase")
        status, color, msg = check_supabase()
        render_status("Supabase Backend", status, color, msg)

    with col3:
        st.subheader("n8n")
        status, color, msg = check_n8n()
        render_status("n8n Workflows", status, color, msg)

    if st.button("Обновить статусы"):
        st.rerun()

if __name__ == "__main__":
    health_dashboard_page()
