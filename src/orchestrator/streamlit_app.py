import streamlit as st
import json
from datetime import datetime
import time # Для имитации задержки ответа Katana

# --- Инициализация состояния ---
def init_session_state():
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'chat_visible' not in st.session_state:
        st.session_state.chat_visible = False
    if 'monitoring_visible' not in st.session_state:
        st.session_state.monitoring_visible = True
    if 'user_input' not in st.session_state:
        st.session_state.user_input = ""

def load_data(filepath: str) -> list[dict]:
    """Loads and parses the JSON log file."""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        st.error(f"Error: The file '{filepath}' was not found. Please make sure it exists in the correct location.")
        return []
    except json.JSONDecodeError:
        st.error(f"Error: Could not decode JSON from '{filepath}'. Please check the file format.")
        return []
    except Exception as e:
        st.error(f"An unexpected error occurred while loading the data: {e}")
        return []

def display_round_data(round_data: dict):
    """Displays the data for a single round using st.expander."""
    round_number = round_data.get('round', 'N/A')
    with st.expander(f"Round {round_number}"):
        st.metric(label="Round Number", value=str(round_number))
        st.metric(label="Batch Size", value=str(round_data.get('batch_size', 'N/A')))
        st.metric(label="Avg. Time per Task (s)", value=f"{round_data.get('avg_time_per_task_seconds', 'N/A'):.2f}" if isinstance(round_data.get('avg_time_per_task_seconds'), (int, float)) else 'N/A')

        error_types = round_data.get('error_types_in_batch', [])
        if isinstance(error_types, dict): # Assuming errors might be a dict {type: count}
            st.write("Error Types in Batch:")
            for error_type, count in error_types.items():
                st.write(f"- {error_type}: {count}")
        elif isinstance(error_types, list) and error_types: # Assuming errors might be a list of strings
            st.write("Error Types in Batch:")
            for error_type in error_types:
                st.write(f"- {error_type}")
        elif not error_types:
            st.write("Error Types in Batch: None")
        else:
            st.write(f"Error Types in Batch: {error_types}")


        start_time_str = round_data.get('start_time')
        end_time_str = round_data.get('end_time')

        st.write(f"Start Time: {start_time_str if start_time_str else 'N/A'}")
        st.write(f"End Time: {end_time_str if end_time_str else 'N/A'}")

        if start_time_str and end_time_str:
            try:
                # Attempt to parse ISO format datetime strings
                start_time_dt = datetime.fromisoformat(start_time_str)
                end_time_dt = datetime.fromisoformat(end_time_str)
                duration = end_time_dt - start_time_dt
                st.metric(label="Duration", value=str(duration))
            except ValueError:
                st.warning("Could not parse timestamps to calculate duration. Ensure they are in ISO format (YYYY-MM-DDTHH:MM:SS.ffffff).")
            except Exception as e:
                st.error(f"Error calculating duration: {e}")
        else:
            st.write("Duration: N/A (Missing start or end time)")

def main():
    """Main function to run the Streamlit application."""
    st.set_page_config(page_title="Katana Orchestrator Dashboard", layout="wide")
    init_session_state() # Инициализация состояния сессии

    # --- Боковая панель для управления видимостью ---
    with st.sidebar:
        st.header("Управление панелями")
        if st.button("Toggle Chat Window", key="toggle_chat_btn"):
            st.session_state.chat_visible = not st.session_state.chat_visible

        if st.button("Toggle Monitoring Dashboard", key="toggle_monitoring_btn"):
            st.session_state.monitoring_visible = not st.session_state.monitoring_visible

        st.markdown("---") # Разделитель

    # --- Основной контент ---
    main_container = st.container()

    with main_container:
        st.title("Katana Orchestrator Dashboard & Chat")

    # --- Чат-интерфейс (может быть в сайдбаре или как плавающее окно) ---
    # Для простоты пока разместим его под дашбордом или сбоку, если дашборд скрыт.
    # Более сложное позиционирование (например, кнопка в углу) требует CSS/HTML.

    if st.session_state.chat_visible:
        chat_container = st.expander("Katana Chat", expanded=True)
        with chat_container:
            # Отображение истории сообщений
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            # Поле ввода пользователя
            def handle_submit():
                user_message_content = st.session_state.current_user_input # Получаем значение из ключа
                if user_message_content:
                    # Добавляем сообщение пользователя в историю
                    st.session_state.messages.append({"role": "user", "content": user_message_content})

                    # Заглушка ответа Katana
                    with st.chat_message("assistant"):
                        st.markdown(f"Katana: Принял: \"{user_message_content}\"")
                        st.session_state.messages.append({"role": "assistant", "content": f"Katana: Принял: \"{user_message_content}\""})

                    # Очищаем поле ввода после отправки
                    st.session_state.current_user_input = ""

            st.text_input("Ваше сообщение:", key="current_user_input", on_change=handle_submit)

            # Кнопка "Отправить" - теперь обработка идет через on_change text_input
            # if st.button("Отправить", key="send_chat_message"):
            #    handle_submit(st.session_state.user_input) # Передаем текущее значение

    # --- Дашборд Мониторинга ---
    if st.session_state.monitoring_visible:
        dashboard_container = st.container()
        with dashboard_container:
            st.header("Orchestrator Monitoring")
            log_file_path = "orchestrator_log.json"
            orchestrator_data = load_data(log_file_path)

            if orchestrator_data:
                st.success(f"Successfully loaded {len(orchestrator_data)} round(s) from '{log_file_path}'.")
                for round_entry in orchestrator_data:
                    display_round_data(round_entry)
            else:
                st.info("No data to display. Ensure 'orchestrator_log.json' exists and is correctly formatted.")
    elif not st.session_state.chat_visible and not st.session_state.monitoring_visible:
        st.info("Обе панели (Чат и Мониторинг) скрыты. Используйте кнопки в боковой панели для их отображения.")

if __name__ == "__main__":
    main()
