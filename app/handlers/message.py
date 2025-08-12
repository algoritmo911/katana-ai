from aiogram import Router, types, F
from aiogram.filters import Command
from loguru import logger

# These are the legacy modules. We will import them for now,
# but the long-term goal (as per the directive) is to replace
# them with more advanced integrations.
import nlp_module
import katana_agent

router = Router(name="message_handlers")


@router.message(Command("run"))
async def handle_run_command(message: types.Message):
    """
    Handler for the /run <command> command.
    Extracts the command text and passes it to the Katana agent.
    """
    # The command text is everything after "/run "
    command_text = message.text[len("/run "):].strip()
    user = message.from_user

    logger.info(f"User {user.full_name} (ID: {user.id}) issued /run command: '{command_text}'")

    if not command_text:
        await message.answer("Необходимо указать команду для выполнения. \nИспользование: <code>/run &lt;команда&gt;</code>")
        return

    try:
        # The directive implies direct execution via Katana agent.
        # We will pass the raw command text for now.
        # The `params` argument can be enriched with more context later.
        response_message = katana_agent.execute_command(
            command_text,
            params={"source": "telegram_run_command", "user_id": user.id}
        )
    except Exception as e:
        logger.exception(f"Error executing /run command for user {user.id}")
        response_message = f"Произошла ошибка при выполнении команды: <code>{command_text}</code>."

    await message.answer(response_message)


@router.message(F.text)
async def handle_text_message(message: types.Message):
    """
    Handler for general text messages (not commands).
    It uses the NLP module to understand intent and then executes a command.
    """
    message_text = message.text
    user = message.from_user
    logger.info(f"Received text message from {user.full_name} (ID: {user.id}): '{message_text}'")

    response_message = ""
    try:
        # 1. Use NLP module to get intent and parameters
        intent, params = nlp_module.recognize_intent(message_text)
        logger.debug(f"NLP result: intent='{intent}', params={params}")

        # 2. Route to Katana agent based on intent
        if intent:
            # We pass the recognized intent as the command to the agent
            response_message = katana_agent.execute_command(intent, params)
        else:
            # Fallback if intent is not recognized
            response_message = "Я не смог распознать ваше намерение. Попробуйте переформулировать или используйте <code>/help</code>."

    except Exception as e:
        logger.exception(f"Error processing text message from user {user.id}")
        response_message = "К сожалению, при обработке вашего запроса произошла внутренняя ошибка."

    await message.answer(response_message)
