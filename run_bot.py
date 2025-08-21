import os
import telebot
from bot.katana_bot import bot, load_user_state, save_user_state, user_memory, log_local_bot_event
from bot.dialog_graph import DialogGraph

# --- Дополнительные команды для тестирования ---

@bot.message_handler(commands=['get_graph'])
def handle_get_graph(message):
    """Отправляет визуализацию графа диалога."""
    chat_id = message.chat.id
    if chat_id in user_memory and "dialog_graph" in user_memory[chat_id]:
        dialog_graph = user_memory[chat_id]["dialog_graph"]
        try:
            # Визуализируем граф
            file_path = dialog_graph.visualize(filename=f"temp_graph_{chat_id}.png")

            # Отправляем фото
            with open(file_path, 'rb') as photo:
                bot.send_photo(chat_id, photo, caption="Вот текущий граф вашего диалога.")

            # Удаляем временный файл
            os.remove(file_path)
            log_local_bot_event(f"Sent dialog graph visualization to {chat_id}")

        except Exception as e:
            bot.reply_to(message, f"Не удалось сгенерировать граф: {e}")
            log_local_bot_event(f"Failed to generate graph for {chat_id}: {e}")
    else:
        bot.reply_to(message, "Ваша история диалога еще не начата.")

@bot.message_handler(commands=['reset_me'])
def handle_reset(message):
    """Сбрасывает состояние для текущего пользователя."""
    chat_id = message.chat.id
    if chat_id in user_memory:
        del user_memory[chat_id]
        save_user_state()
        bot.reply_to(message, "Ваше состояние было сброшено. Начните диалог с /start.")
        log_local_bot_event(f"Reset state for user {chat_id}")
    else:
        bot.reply_to(message, "У вас нет сохраненного состояния для сброса.")


if __name__ == '__main__':
    log_local_bot_event("Bot starting...")
    load_user_state()

    # Чтобы бот мог использовать команды из этого файла, их нужно зарегистрировать.
    # pyTelegramBotAPI делает это автоматически для хендлеров в том же файле, где создан bot.
    # Так как мы импортируем bot, он уже "знает" о хендлерах из katana_bot.py.
    # Хендлеры из этого файла также будут добавлены.

    try:
        log_local_bot_event("Bot polling started.")
        bot.infinity_polling(logger_level=None)
    except Exception as e:
        log_local_bot_event(f"An error occurred during polling: {e}")
    finally:
        save_user_state()
        log_local_bot_event("Bot stopped and user state saved.")
