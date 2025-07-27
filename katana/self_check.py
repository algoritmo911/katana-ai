from pathlib import Path, PurePath
from dotenv import load_dotenv
import os, sys, subprocess
from katana.logger import get_logger

CRITICAL = False
log = get_logger("katana.selfcheck")

CHECKS = []

def check(msg):
    def decorator(fn):
        CHECKS.append((msg, fn)); return fn
    return decorator

@check(".env file present")
def _check_env_file():
    if not Path('.env').exists():
        raise FileNotFoundError('.env missing')

@check("no __pycache__ committed")
def _check_pyc():
    for p in Path('.').rglob('*.pyc'):
        raise RuntimeError(f'Found pyc: {p}')

@check("Redis available")
def _check_redis():
    import redis
    try:
        redis.Redis.from_url(os.environ['REDIS_URL']).ping()
    except redis.exceptions.ConnectionError as e:
        raise RuntimeError(f"Redis connection failed: {e}")
    except Exception as e:
        raise RuntimeError(f"An unexpected error occurred with Redis: {e}")

@check("Telegram Bot token valid")
def _check_telegram():
    import telegram
    try:
        bot = telegram.Bot(token=os.environ['TELEGRAM_TOKEN'])
        bot.get_me()
    except Exception as e:
        raise RuntimeError(f"Telegram connection failed: {e}")

@check("Dependencies fresh")
def _check_dependencies():
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--dry-run', '-r', 'katana/requirements.txt'], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Dependency check failed: {e.output}")

@check("Project structure valid")
def _check_project_structure():
    expected_dirs = ['katana', 'katana/api', 'katana/bot', 'katana/core', 'katana/services', 'katana/tests', 'katana/utils']
    for d in expected_dirs:
        if not Path(d).is_dir():
            raise NotADirectoryError(f"Expected directory not found: {d}")

@check("Logs directory exists")
def _check_logs():
    if not Path('logs').is_dir():
        raise NotADirectoryError("Logs directory not found")

@check("Tests pass")
def _check_tests():
    try:
        subprocess.run([sys.executable, '-m', 'pytest'], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Tests failed: {e.output}")

def run_all():
    global CRITICAL
    for msg, fn in CHECKS:
        try:
            fn(); log.info(f"✅ {msg}")
        except Exception as e:
            log.error(f"❌ {msg}: {e}")
            CRITICAL = True
    if CRITICAL:
        sys.exit(1)

if __name__ == '__main__':
    run_all()
