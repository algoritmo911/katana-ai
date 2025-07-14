import telebot
import os

API_TOKEN = os.getenv('KATANA_TELEGRAM_TOKEN')

if not API_TOKEN:
    raise ValueError("KATANA_TELEGRAM_TOKEN environment variable not set!")

bot = telebot.TeleBot(API_TOKEN)
