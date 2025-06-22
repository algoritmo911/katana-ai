import os
import logging
from dotenv import load_dotenv

# Настройка логирования до загрузки остальных модулей бота, чтобы видеть все с самого начала
# Устанавливаем базовый уровень INFO, чтобы видеть сообщения от python-dotenv и нашего бота
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info("Attempting to load environment variables from .env file...")
# Загружаем переменные окружения из .env файла
# Это должно быть сделано до импорта bot.katana_bot, так как он ожидает, что переменные уже установлены
if load_dotenv():
    logger.info("✅ .env file loaded successfully.")
else:
    logger.warning("⚠️ .env file not found or is empty. Relying on system environment variables.")

# Теперь, когда переменные окружения (предположительно) загружены, импортируем бота
try:
    from bot.katana_bot import bot, logger as bot_logger # Импортируем и логгер бота для консистентности
    # Можно настроить логгер бота здесь дополнительно, если нужно
except ImportError as e:
    logger.error(f"❌ Failed to import bot.katana_bot. Ensure it exists and PYTHONPATH is set correctly. Error: {e}", exc_info=True)
    exit(1)
except Exception as e:
    logger.error(f"❌ An unexpected error occurred during bot import: {e}", exc_info=True)
    exit(1)


if __name__ == '__main__':
    logger.info("🚀 Starting Katana Bot locally...")
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
        logger.info("🛑 Katana Bot has shut down.")
