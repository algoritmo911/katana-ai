import argparse
import logging
import os
import sys
from datetime import datetime, timezone

# --- Настройка путей для импорта ---
# Это необходимо, чтобы runner.py мог найти другие модули проекта (MemoryManager, collector),
# когда он запускается как скрипт.
# Предполагается, что runner.py находится в src/monitoring/fatigue_analyzer/
# и корень проекта (содержащий src/) должен быть в sys.path.
# Получаем путь к директории src/
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.abspath(os.path.join(current_dir, "../../..")) # src/monitoring/fatigue_analyzer -> src/monitoring -> src -> корень_проекта/src

if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
# --- Конец настройки путей ---

try:
    from memory.memory_manager import MemoryManager # Ожидается, что src.memory.memory_manager
    # Проверка, что это не заглушка из collector.py, если вдруг она там осталась глобальной
    if 'collector' in MemoryManager.__module__:
        raise ImportError("Imported MemoryManager seems to be a mock from collector.")
    logger_runner = logging.getLogger(__name__)
    logger_runner.debug("Successfully imported REAL MemoryManager in runner.")
except ImportError as e:
    # Если реальный MemoryManager не найден, используем заглушку из collector
    # Это в основном для тестирования runner.py без настроенного Redis
    logger_runner = logging.getLogger(__name__) # Инициализируем логгер до попытки импорта collector
    logger_runner.warning(f"Could not import real MemoryManager in runner: {e}. "
                          "Will rely on MOCK MemoryManager in FatigueCollector if real one isn't found there either.")
    # FatigueCollector сам попытается импортировать MemoryManager или использовать свою заглушку.
    # Нам не нужно здесь определять еще одну заглушку.
    pass

from monitoring.fatigue_analyzer.collector import FatigueCollector, LocalFileStorage, MemoryManager as FallbackMockMemoryManager
# Если реальный MemoryManager не был импортирован выше, FatigueCollector может использовать свой MOCK.
# FallbackMockMemoryManager импортируется для случая, если даже collector не смог найти реальный MM,
# и нам нужен тип для аннотации или инстанцирования здесь (хотя collector это сделает сам).


# Настройка логирования для runner
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)] # Вывод в stdout
)
logger = logging.getLogger(__name__) # Логгер для этого файла

def main():
    """
    Главная функция для запуска анализатора усталости из командной строки.
    """
    parser = argparse.ArgumentParser(description="Katana Fatigue Analyzer")
    parser.add_argument(
        "--chat-id",
        type=str,
        required=True, # Сделаем обязательным для MVP, чтобы не усложнять поиск всех chat_id
        help="Chat ID of the user to analyze."
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save the analysis results to a JSON file."
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="fatigue_analysis_report.json",
        help="Path to the output JSON file (default: fatigue_analysis_report.json in current dir)."
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (default: INFO)."
    )
    # Аргументы для подключения к Redis, если MemoryManager их требует
    # и они не берутся из переменных окружения по умолчанию в MemoryManager
    parser.add_argument("--redis-host", type=str, default=os.getenv('REDIS_HOST', 'localhost'), help="Redis host.")
    parser.add_argument("--redis-port", type=int, default=int(os.getenv('REDIS_PORT', '6379')), help="Redis port.")
    parser.add_argument("--redis-db", type=int, default=int(os.getenv('REDIS_DB', '0')), help="Redis DB number.")
    parser.add_argument("--redis-password", type=str, default=os.getenv('REDIS_PASSWORD', None), help="Redis password.")


    args = parser.parse_args()

    # Установка уровня логирования
    logging.getLogger().setLevel(args.log_level) # Для корневого логгера
    logger.info(f"Logging level set to: {args.log_level}")

    logger.info(f"Starting fatigue analysis for chat_id: {args.chat_id}")

    # Инициализация MemoryManager
    # Используем переменные окружения или значения по умолчанию, если не переданы аргументы
    try:
        # Попытка инициализировать реальный MemoryManager
        # Предполагается, что MemoryManager читает env vars или принимает параметры
        mm_instance = MemoryManager(
            host=args.redis_host,
            port=args.redis_port,
            db=args.redis_db,
            password=args.redis_password
        )
        logger.info(f"Using MemoryManager connected to Redis at {args.redis_host}:{args.redis_port}/{args.redis_db}")
        # Проверка соединения (если есть метод ping или подобный)
        # if hasattr(mm_instance, 'redis_client') and mm_instance.redis_client:
        #     mm_instance.redis_client.ping()
        # logger.info("Redis connection successful.")

    except redis.exceptions.ConnectionError as e: # type: ignore # Если redis не импортирован здесь
        logger.error(f"Failed to connect to Redis: {e}. Using MOCK MemoryManager as fallback for analysis.")
        mm_instance = FallbackMockMemoryManager() # Используем заглушку из collector.py
    except NameError: # Если 'MemoryManager' не был успешно импортирован (остался как заглушка)
        logger.warning("Real MemoryManager class not found, using MOCK MemoryManager for analysis.")
        mm_instance = FallbackMockMemoryManager() # Используем заглушку из collector.py
    except Exception as e:
        logger.error(f"Error initializing MemoryManager: {e}. Using MOCK MemoryManager as fallback.")
        mm_instance = FallbackMockMemoryManager()


    # Инициализация FatigueCollector
    collector = FatigueCollector(memory_manager=mm_instance)

    # Выполнение анализа
    fatigue_reports = collector.process_user_fatigue(args.chat_id)

    if not fatigue_reports:
        logger.info(f"No fatigue reports generated for chat_id: {args.chat_id}.")
        return

    # Вывод результатов в консоль
    logger.info(f"\n--- Fatigue Analysis Results for chat_id: {args.chat_id} ---")
    for i, report in enumerate(fatigue_reports):
        logger.info(f"\nReport {i+1}/{len(fatigue_reports)} (Session ID: {report.session_id}):")
        # Используем model_dump_json для Pydantic V2 или .json() для V1
        try:
            print(report.model_dump_json(indent=2))
        except AttributeError:
            print(report.json(indent=2))


    # Сохранение результатов в файл, если указан флаг --save
    if args.save:
        # Обеспечение корректного пути к файлу отчета
        output_filepath = args.output_file
        if not os.path.isabs(output_filepath):
            # Если путь относительный, делаем его относительно директории, откуда запущен runner.py
            # или лучше, относительно корня проекта, если это возможно определить.
            # Для простоты, пока относительно текущей рабочей директории.
            output_filepath = os.path.join(os.getcwd(), output_filepath)

        # Создаем директорию, если она не существует
        output_dir = os.path.dirname(output_filepath)
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
                logger.info(f"Created directory for output file: {output_dir}")
            except OSError as e:
                logger.error(f"Failed to create directory {output_dir}: {e}")
                # Продолжаем попытку сохранить в текущей директории, если создание не удалось
                output_filepath = os.path.basename(output_filepath)


        logger.info(f"Saving analysis results to: {os.path.abspath(output_filepath)}")
        storage = LocalFileStorage(filepath=output_filepath)
        storage.save_batch(fatigue_reports)
    else:
        logger.info("Results not saved to file (use --save option).")

    logger.info("Fatigue analysis finished.")

if __name__ == "__main__":
    # Пример запуска:
    # python -m src.monitoring.fatigue_analyzer.runner --chat-id test_chat_with_data --save --output-file reports/fatigue_report_test.json --log-level DEBUG
    #
    # Для использования с реальным Redis, убедитесь, что Redis запущен и доступен,
    # и что переменные окружения REDIS_HOST, REDIS_PORT и т.д. установлены,
    # или передайте их через аргументы командной строки.
    main()
