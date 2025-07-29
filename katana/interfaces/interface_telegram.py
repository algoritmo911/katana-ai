import logging
from telegram import Update as TelegramUpdate
from telegram.ext import Application
from katana.message_dispatcher import MessageDispatcher

logger = logging.getLogger(__name__)


class TelegramInterface:
    def __init__(self, token, webhook_url, dispatcher: MessageDispatcher):
        self.app = Application.builder().token(token).build()
        self.webhook_url = webhook_url
        self.dispatcher = dispatcher

    async def set_webhook(self):
        try:
            await self.app.bot.set_webhook(
                url=self.webhook_url,
                allowed_updates=TelegramUpdate.ALL_TYPES,
                drop_pending_updates=True,
            )
            logger.info(f"Webhook successfully set to {self.webhook_url}")
            return True
        except Exception as e:
            logger.error(
                f"Failed to set webhook to {self.webhook_url}: {e}", exc_info=True
            )
            return False

    async def handle_update(self, data):
        tg_update = TelegramUpdate.de_json(data, self.app.bot)
        logger.debug(f"Received raw update data: {data}")
        logger.info(f"Processing Telegram update ID: {tg_update.update_id}")

        if tg_update.message and tg_update.message.text:
            message = tg_update.message.text
            user_id = tg_update.message.chat_id
            response = await self.dispatcher.dispatch("telegram", user_id, message)
            if response:
                await self.app.bot.send_message(chat_id=user_id, text=response)
        elif tg_update.message:
            await self.app.bot.send_message(
                chat_id=tg_update.message.chat_id,
                text="I can currently only process text commands.",
            )
