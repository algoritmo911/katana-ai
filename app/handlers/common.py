from aiogram import Router, types
from aiogram.filters import CommandStart, Command

# Create a new Router instance for common handlers
router = Router(name="common_handlers")


@router.message(CommandStart())
async def handle_start(message: types.Message):
    """
    Handler for the /start command.
    Sends a welcome message to the user.
    """
    user = message.from_user
    # The `mention_html()` method creates a user-mention link
    await message.answer(f"Привет, {user.mention_html()}!")
    # Also send the help text after the welcome message
    await handle_help(message)


@router.message(Command("help"))
async def handle_help(message: types.Message):
    """
    Handler for the /help command.
    Sends a help message with instructions on how to use the bot.
    """
    help_text = (
        "<b>Симбиот 'Катана' к вашим услугам.</b>\n\n"
        "Я - ваш прямой интерфейс к экосистеме. "
        "Понимаю как прямые команды, так и естественный язык.\n\n"
        "<b>Примеры команд:</b>\n"
        "• <code>/run &lt;команда&gt;</code> - прямое исполнение директивы.\n"
        "  (например, <code>/run system check</code>)\n"
        "• <code>/status [service_name]</code> - статус сервиса (Этап 6).\n"
        "• <code>/trace [trace_id]</code> - трассировка операции (Этап 6).\n\n"
        "Просто опишите вашу цель, и я приступлю к исполнению."
    )
    await message.answer(help_text)
