# bot/commands/__init__.py
import os
import importlib
import inspect
from pathlib import Path

# Словарь для хранения зарегистрированных обработчиков команд (intent -> handler)
_command_handlers = {}

# Словарь для хранения метаданных команд (intent -> metadata)
_command_metadata = {}

def register_command(intent, metadata=None):
    """
    Декоратор для регистрации обработчика команды.

    :param intent: Имя намерения (intent), на которое реагирует команда.
    :param metadata: Словарь с дополнительными данными (например, описание).
    """
    def decorator(func):
        if intent in _command_handlers:
            print(f"Warning: Command for intent '{intent}' is being overridden.")
        _command_handlers[intent] = func
        _command_metadata[intent] = metadata or {}
        return func
    return decorator

def get_handler(intent):
    """
    Возвращает обработчик для указанного намерения.
    """
    return _command_handlers.get(intent)

def get_all_commands_metadata():
    """
    Возвращает метаданные всех зарегистрированных команд.
    """
    return _command_metadata

def load_commands():
    """
    Автоматически загружает все модули команд из этой директории.
    """
    commands_dir = Path(__file__).parent

    for filename in os.listdir(commands_dir):
        # Пропускаем __init__.py и другие не-Python файлы
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = f"bot.commands.{filename[:-3]}"
            try:
                importlib.import_module(module_name)
                print(f"Successfully loaded command module: {module_name}")
            except Exception as e:
                print(f"Error loading command module {module_name}: {e}")

# Выполняем загрузку команд при инициализации пакета
load_commands()