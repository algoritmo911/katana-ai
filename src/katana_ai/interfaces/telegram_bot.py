import os
import telebot
from telebot import types
from src.katana_ai.predict.trading_strategy import TradingStrategy
from src.katana_ai.adapters.n8n_bus import N8nBus

class TelegramBot:
    def __init__(self, telegram_token=None, n8n_webhook_url=None):
        self.token = telegram_token or os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            raise ValueError("Telegram bot token must be provided.")

        self.bot = telebot.TeleBot(self.token)
        self.trading_strategy = TradingStrategy() # Assumes no specific data source for now
        self.n8n_bus = N8nBus(webhook_url=n8n_webhook_url)

        # This will store the trade suggestion per user/chat
        self.pending_suggestions = {}

        # Register handlers
        self.register_handlers()

    def register_handlers(self):
        @self.bot.message_handler(commands=['start', 'help'])
        def send_welcome(message):
            self.bot.reply_to(message, "Welcome to Katana AI Trading Bot. Use /trade to get a new trading suggestion.")

        @self.bot.message_handler(commands=['trade'])
        def suggest_trade(message):
            chat_id = message.chat.id
            suggestion = self.trading_strategy.analyze_market_and_suggest_action()

            if suggestion['action'] != 'HOLD':
                self.pending_suggestions[chat_id] = suggestion
                markup = self.create_suggestion_keyboard(suggestion)
                self.bot.send_message(chat_id, f"New trading suggestion:\n{suggestion['why-trace']}", reply_markup=markup)
            else:
                self.bot.send_message(chat_id, "No significant trading opportunity found at the moment.")

        @self.bot.callback_query_handler(func=lambda call: True)
        def handle_callback_query(call):
            chat_id = call.message.chat.id
            suggestion = self.pending_suggestions.get(chat_id)

            if not suggestion:
                self.bot.answer_callback_query(call.id, "This suggestion has expired or is invalid.")
                return

            if call.data == "confirm":
                self.bot.answer_callback_query(call.id, "Trade confirmed. Sending to execution engine...")
                self.bot.edit_message_text("Trade confirmed. Sending to execution engine...", chat_id, call.message.message_id)

                command_data = {
                    'action': suggestion['action'],
                    'details': suggestion,
                }

                self.n8n_bus.send_command(command_data)
                del self.pending_suggestions[chat_id]

            elif call.data == "decline":
                self.bot.answer_callback_query(call.id, "Trade declined.")
                self.bot.edit_message_text("Trade declined by user.", chat_id, call.message.message_id)
                del self.pending_suggestions[chat_id]

            elif call.data == "explain":
                self.bot.answer_callback_query(call.id)
                explanation = suggestion.get('why-trace', 'No specific reason provided.')
                self.bot.send_message(chat_id, f"Explanation: {explanation}")

    def create_suggestion_keyboard(self, suggestion):
        markup = types.InlineKeyboardMarkup()
        confirm_button = types.InlineKeyboardButton("✅ Confirm", callback_data="confirm")
        decline_button = types.InlineKeyboardButton("❌ Decline", callback_data="decline")
        explain_button = types.InlineKeyboardButton("❓ Explain", callback_data="explain")
        markup.row(confirm_button, decline_button)
        markup.row(explain_button)
        return markup

    def run(self):
        print("Telegram bot is running...")
        self.bot.polling()

if __name__ == '__main__':
    # This allows running the bot directly for testing.
    # Make sure to set environment variables: TELEGRAM_BOT_TOKEN and N8N_WEBHOOK_URL
    print("Starting bot...")
    bot = TelegramBot()
    bot.run()
