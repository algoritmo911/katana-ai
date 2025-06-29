import streamlit as st
import logging
import os
from katana import generate_patch # Import the stub function

# Setup logging
LOG_DIR = "logs" # Relative to app.py, so it will be alg911.catana-ai/logs
LOG_FILE = os.path.join(LOG_DIR, "bot_interactions.log")

# Ensure log directory exists - created by previous bash command.
# os.makedirs(LOG_DIR, exist_ok=True) # Keep this commented as per previous logic

logger = logging.getLogger("KatanaBotLogger")
logger.setLevel(logging.INFO)

if not logger.handlers:
    # Ensure the LOG_DIR is interpreted correctly from the script's location
    # For streamlit, cwd might be different, so construct path from script file.
    script_dir = os.path.dirname(__file__)
    full_log_dir = os.path.join(script_dir, LOG_DIR)
    os.makedirs(full_log_dir, exist_ok=True) # Ensure dir exists here before handler
    full_log_file_path = os.path.join(full_log_dir, "bot_interactions.log")

    file_handler = logging.FileHandler(full_log_file_path)
    formatter = logging.Formatter('%(asctime)s - Question: %(message)s') # Updated format
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

def main():
    st.title("Katana Bot Interface")

    user_question = st.text_input("Ваш вопрос Катане:")

    if st.button("Спроси Катану"):
        if user_question:
            st.write(f"Вы спросили: {user_question}")

            # Call Katana's generate_patch function
            bot_response = generate_patch(user_question)

            # Log interaction (question and response)
            # The logger format now includes "Question: ", so we log "actual_question - Response: actual_response"
            logger.info(f"{user_question} - Response: {bot_response}")

            st.info(bot_response)
        else:
            st.warning("Пожалуйста, введите вопрос.")

if __name__ == "__main__":
    main()
