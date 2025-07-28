import os
from dotenv import load_dotenv
from src.utils.standard_logger import get_logger

# Set up logger for this script
logger = get_logger(__name__)

logger.info("Attempting to load environment variables from .env file...")
# Load environment variables from .env file
# This should be done before importing bot.katana_bot, as it expects the variables to be set
if load_dotenv(): # `load_dotenv` will find the .env file itself
    logger.info("✅ .env file loaded successfully (or was already loaded).")
else:
    logger.warning("⚠️ .env file not found. Relying on system environment variables if already set.")

# Теперь, когда переменные окружения (предположительно) загружены, импортируем бота
try:
    # Импортируем логгер бота, чтобы он также унаследовал файловый обработчик, если настроен
    from bot.katana_bot import bot, logger as bot_logger, start_heartbeat_thread, stop_heartbeat_thread
    # Если в bot.katana_bot своя конфигурация логирования, она может перезаписать эту.
    # Убедимся, что katana_bot использует тот же logger или настраивается согласованно.
    # В текущей реализации katana_bot.py использует logging.getLogger(__name__),
    # так что он должен наследовать обработчики от корневого логгера.
except ImportError as e:
    logger.error(f"❌ Failed to import from bot.katana_bot. Ensure it exists and PYTHONPATH is set correctly. Error: {e}", exc_info=True)
    exit(1)
except Exception as e:
    logger.error(f"❌ An unexpected error occurred during bot import: {e}", exc_info=True)
    exit(1)


if __name__ == '__main__':
    logger.info("🚀 Starting Katana Bot locally...")
    start_heartbeat_thread() # Start the heartbeat thread
    try:
        # bot.polling() в katana_bot.py уже настроен с none_stop=True
        # и содержит свое логирование старта.
        # Просто вызываем его здесь.
        # bot.polling() является блокирующим вызовом.
        bot_logger.info("Starting bot polling (from run_bot_locally.py)...") # Используем логгер бота
        bot.polling()
        # Этот код ниже не будет достигнут, если polling работает в режиме none_stop=True
        # и не остановлен явно или ошибкой (которую none_stop=True должен предотвратить от остановки polling)
        logger.info("Katana Bot polling has finished or been interrupted.")
    except KeyboardInterrupt:
        logger.info("🤖 Bot polling interrupted by user (Ctrl+C). Shutting down...")
    except Exception as e:
        # Эта секция не должна срабатывать, если none_stop=True работает как ожидается
        # и глобальный обработчик в katana_bot.py ловит все ошибки внутри обработчиков сообщений.
        # Но на всякий случай, если ошибка произойдет на уровне самого polling или инициализации.
        logger.error(f"💥 An unexpected error occurred while running the bot: {e}", exc_info=True)
    finally:
        logger.info("Initiating shutdown sequence...")
        stop_heartbeat_thread() # Stop the heartbeat thread
        # Considerations for further graceful shutdown:
        # - If message handlers were run in separate threads managed by this application,
        #   we could signal them to complete and join them here.
        # - For pyTelegramBotAPI's default polling, active handlers might be interrupted.
        # - Ensure any external resources (DB connections, files) are closed if opened directly.
        logger.info("🛑 Katana Bot has shut down.")
