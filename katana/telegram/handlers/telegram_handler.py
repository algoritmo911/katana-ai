from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, Updater
from katana.agents.suggest_agent import SuggestAgent

class TelegramHandler:
    def __init__(self, token: str):
        self.suggest_agent = SuggestAgent()
        self.updater = Updater(token=token, use_context=True)
        self.dp = self.updater.dispatcher
        self.dp.add_handler(CommandHandler("start", self.start))
        self.dp.add_handler(MessageHandler(Filters.text & ~Filters.command, self.handle_message))
        self.dp.add_handler(CallbackQueryHandler(self.handle_callback))

    def start(self, update: Update, context: CallbackContext):
        update.message.reply_text(
            "Привет! Я Katana Suggest Agent. Напиши что-нибудь, и я помогу с командами."
        )

    def handle_message(self, update: Update, context: CallbackContext):
        user_input = update.message.text
        suggestions = self.suggest_agent.suggest(user_input, mode="static")

        if not suggestions:
            update.message.reply_text("Нет подсказок для этого запроса.")
            return

        keyboard = [
            [InlineKeyboardButton(cmd, callback_data=cmd)] for cmd in suggestions
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text("Возможно, тебе подойдут эти команды:", reply_markup=reply_markup)

    def handle_callback(self, update: Update, context: CallbackContext):
        query = update.callback_query
        query.answer()
        selected_command = query.data
        # Здесь можно сразу выполнить команду или показать детали
        query.edit_message_text(text=f"Ты выбрал команду:\n`{selected_command}`", parse_mode='Markdown')

    def run(self):
        self.updater.start_polling()
        self.updater.idle()

# Если хочешь запустить отдельно:
# if __name__ == "__main__":
#     token = "<YOUR_TELEGRAM_BOT_TOKEN>"
#     handler = TelegramHandler(token)
#     handler.run()
