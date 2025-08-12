import telebot
import json
import os
from pathlib import Path
from datetime import datetime

# --- Новые импорты "Цербера" ---
from pydantic import ValidationError
from katana.core.contracts.commands import get_command_model
from katana.core.logging import logger
# --- Конец импортов "Цербера" ---

from bot_components.handlers.log_event_handler import handle_log_event
from bot_components.handlers.ping_handler import handle_ping
from bot_components.handlers.mind_clearing_handler import handle_mind_clearing

# TODO: Get API token from environment variable or secrets manager
API_TOKEN = '123:dummy_token'  # Placeholder for tests

bot = telebot.TeleBot(API_TOKEN)

# Directory for storing command files
COMMAND_FILE_DIR = Path('commands')
COMMAND_FILE_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------------------
# Старая функция логирования УДАЛЕНА. Теперь используется `logger` из `katana.core.logging`
# ------------------------------------------------------------------------------

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """
    "Гермес" (Command Engine) - точка входа для всех команд.
    Теперь с интегрированным "Стражем Входа" (Pydantic-валидация).
    """
    chat_id = message.chat.id
    command_text = message.text

    logger.info(
        "Received message",
        chat_id=chat_id,
        extra={"command_text": command_text}
    )

    try:
        command_data = json.loads(command_text)
    except json.JSONDecodeError:
        error_msg = "Error: Invalid JSON format."
        bot.reply_to(message, error_msg)
        logger.error(
            "Invalid JSON format",
            chat_id=chat_id,
            extra={"command_text": command_text}
        )
        return

    # --- "Страж Входа": Предисполнительная Валидация ---
    CommandModel = get_command_model(command_data)
    if not CommandModel:
        error_msg = f"Error: Unknown command type '{command_data.get('type')}'."
        bot.reply_to(message, error_msg)
        logger.error(
            "Unknown command type",
            chat_id=chat_id,
            command_type=command_data.get('type'),
            extra={"command_data": command_data}
        )
        return

    try:
        # Здесь происходит магия Pydantic: парсинг и валидация в одном действии.
        # Если данные не соответствуют контракту, Pydantic возбудит исключение ValidationError.
        validated_command = CommandModel.model_validate(command_data)
    except ValidationError as e:
        # В случае провала валидации, генерируем подробный, структурированный лог
        # и отправляем пользователю понятное сообщение об ошибке.
        error_msg = f"Validation Error for command '{command_data.get('type')}':\n"
        # Форматируем ошибки для пользователя, создавая полный путь к полю
        error_details = "\n".join([f"- {' -> '.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
        bot.reply_to(message, error_msg + error_details)

        logger.error(
            "Command validation failed",
            chat_id=chat_id,
            command_type=command_data.get('type'),
            command_id=command_data.get('id'),
            extra={"validation_errors": e.errors(), "original_command": command_data}
        )
        return
    # --- Валидация пройдена успешно ---

    logger.info(
        "Command validated successfully",
        chat_id=chat_id,
        command_type=validated_command.type,
        command_id=validated_command.id
    )

    # --- Маршрутизация команд ---
    # Теперь хендлеры получают провалидированный Pydantic-объект, а не сырой dict.
    if validated_command.type == "log_event":
        handle_log_event(validated_command, chat_id, logger)
        bot.reply_to(message, "✅ 'log_event' processed.")
        return
    elif validated_command.type == "ping":
        reply_message = handle_ping(validated_command, chat_id, logger)
        bot.reply_to(message, reply_message)
        return
    elif validated_command.type == "mind_clearing":
        reply_message = handle_mind_clearing(validated_command, chat_id, logger)
        bot.reply_to(message, reply_message)
        return

    # Если тип не совпал (хотя валидатор должен был это отловить), сохраняем.
    # Этот блок остается как fallback, но в идеале никогда не должен выполняться.
    logger.warning(
        f"Command type '{validated_command.type}' not handled by any specific handler, saving to file.",
        chat_id=chat_id,
        command_id=validated_command.id,
        command_type=validated_command.type,
    )

    # Save the command to a file
    timestamp_str = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
    command_file_name = f"{timestamp_str}_{chat_id}.json"

    module_name = validated_command.module
    module_command_dir = COMMAND_FILE_DIR / f"telegram_mod_{module_name}" if module_name != 'telegram_general' else COMMAND_FILE_DIR / 'telegram_general'
    module_command_dir.mkdir(parents=True, exist_ok=True)
    command_file_path = module_command_dir / command_file_name

    with open(command_file_path, "w", encoding="utf-8") as f:
        # Сохраняем уже провалидированные данные
        f.write(validated_command.model_dump_json(indent=2))

    bot.reply_to(message, f"✅ Command received and saved as `{command_file_path}`.")
    logger.info(f"Saved command from {chat_id} to {command_file_path}")


if __name__ == '__main__':
    logger.info("Bot starting...")
    bot.polling()
    logger.info("Bot stopped.")
