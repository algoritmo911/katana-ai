import os
import logging
from dotenv import load_dotenv

# Настройка логирования до загрузки остальных модулей бота, чтобы видеть все с самого начала
# Устанавливаем базовый уровень INFO
log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
log_level = getattr(logging, log_level_str, logging.INFO)

# Базовая конфигурация для вывода в консоль
logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__) # Логгер для этого скрипта

# Настройка логирования в файл, если указано в .env
LOG_FILE_PATH = os.getenv('LOG_FILE_PATH')
if LOG_FILE_PATH:
    try:
        # Убедимся, что директория для лог-файла существует
        os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)

        # Создаем файловый обработчик
        file_handler = logging.FileHandler(LOG_FILE_PATH, mode='a', encoding='utf-8')
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)

        # Добавляем файловый обработчик к корневому логгеру, чтобы все логгеры писали в файл
        logging.getLogger().addHandler(file_handler)
        logger.info(f"✅ Logging to file enabled: {LOG_FILE_PATH}")
    except Exception as e:
        logger.error(f"❌ Failed to configure file logging to {LOG_FILE_PATH}: {e}", exc_info=True)


logger.info("Attempting to load environment variables from .env file...")
# Загружаем переменные окружения из .env файла
# Это должно быть сделано до импорта bot.katana_bot, так как он ожидает, что переменные уже установлены
if load_dotenv(): # `load_dotenv` сам найдет .env файл
    logger.info("✅ .env file loaded successfully (or was already loaded).")
else:
    logger.warning("⚠️ .env file not found. Relying on system environment variables if already set.")

# Теперь, когда переменные окружения (предположительно) загружены, импортируем бота
try:
    # Импортируем логгер бота, чтобы он также унаследовал файловый обработчик, если настроен
    from bot.katana_bot import bot, logger as bot_logger, start_heartbeat_thread, stop_heartbeat_thread
    from katana.self_heal.orchestrator import SelfHealingOrchestrator
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

    orchestrator = None
    # --- Initialize and start Self-Healing Orchestrator ---
    if os.getenv("SELF_HEAL_ENABLED", "false").lower() == "true":
        logger.info("Self-healing feature is enabled. Initializing orchestrator...")
        try:
            config = {
                "log_file_path": os.getenv("SELF_HEAL_LOG_PATH", LOG_FILE_PATH), # Use main log file by default
                "service_name": os.getenv("SELF_HEAL_SERVICE_NAME"),
                "check_interval_seconds": int(os.getenv("SELF_HEAL_INTERVAL_SECONDS", "60")),
                "error_threshold": int(os.getenv("SELF_HEAL_ERROR_THRESHOLD", "10")),
                "notification_chat_id": os.getenv("SELF_HEAL_NOTIFICATION_CHAT_ID"),
            }
            # Basic validation
            if not config["service_name"] or not config["notification_chat_id"]:
                raise ValueError("SELF_HEAL_SERVICE_NAME and SELF_HEAL_NOTIFICATION_CHAT_ID must be set when self-healing is enabled.")

            orchestrator = SelfHealingOrchestrator(config)
            orchestrator.start()
        except Exception as e:
            logger.error(f"❌ Failed to initialize or start Self-Healing Orchestrator: {e}", exc_info=True)
            # We don't exit here; the bot can still run without the orchestrator.
    else:
        logger.info("Self-healing feature is disabled.")

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
        if orchestrator:
            orchestrator.stop()
        stop_heartbeat_thread() # Stop the heartbeat thread
        # Considerations for further graceful shutdown:
        # - If message handlers were run in separate threads managed by this application,
        #   we could signal them to complete and join them here.
        # - For pyTelegramBotAPI's default polling, active handlers might be interrupted.
        # - Ensure any external resources (DB connections, files) are closed if opened directly.
        logger.info("🛑 Katana Bot has shut down.")
