import asyncio
import os
import logging
import telebot
from telebot.types import Message as TeleMessage  # Rename to avoid conflict
import threading # For running polling in a separate thread
from ..interfaces.interface_base import InterfaceBase # Adjusted import path

logger = logging.getLogger(__name__)

# This will be replaced by the actual NLP response logic later
async def process_user_message(payload: dict) -> dict:
    """Placeholder for processing the user message and generating a response."""
    logger.info(f"process_user_message (placeholder) received payload: {payload}")
    user_text = payload.get("text", "empty message")
    return {"text": f"Echo: {user_text}"}


class TelegramInterface(InterfaceBase):
    def __init__(self, api_token: str):
        if not api_token or ':' not in api_token:
            logger.error("❌ Invalid or missing Telegram API token in TelegramInterface.")
            raise ValueError("❌ Invalid or missing Telegram API token.")
        self.api_token = api_token
        self.bot = telebot.TeleBot(self.api_token)
        self.message_queue = asyncio.Queue()
        self.katana_states = {} # Internal state management for chat history

        # Placeholder for functions that would be moved or refactored from katana_bot.py
from typing import Optional

# ... (other imports remain the same)

# class TelegramInterface(InterfaceBase):
# ... (init remains the same)

        # For now, direct integration of handle_message_impl is complex due to its direct bot.reply_to calls.
        # We will simplify the receive/send loop first.

        # Register handlers
        self._register_handlers()

        # Start polling in a separate thread
        # Ensure an event loop is available for call_soon_threadsafe
        self.main_loop = asyncio.get_event_loop()
        self.polling_thread = threading.Thread(target=self._run_polling, daemon=True)
        self.polling_thread.start()
        logger.info("TelegramInterface initialized and polling thread started.")

    def _register_handlers(self):
        @self.bot.message_handler(func=lambda message: True)
        def _handle_all_messages(telegram_message: TeleMessage):
            logger.info(f"TG Interface: Received message from chat_id {telegram_message.chat.id}")
            payload = {
                "chat_id": telegram_message.chat.id,
                "user_id": telegram_message.from_user.id,
                "username": telegram_message.from_user.username,
                "text": telegram_message.text,
                "original_message": telegram_message
            }
            # Use the stored main_loop for call_soon_threadsafe
            if self.main_loop and self.main_loop.is_running():
                 self.main_loop.call_soon_threadsafe(self.message_queue.put_nowait, payload)
            else:
                # This case is problematic if the main event loop isn't running when a message comes in.
                # For initial setup, we assume the main loop is running.
                # A more robust solution might involve a different queue or ensuring loop is passed.
                logger.warning("TG Interface: Main event loop not running or not set when trying to queue message. Message might be lost.")


    def _run_polling(self):
        logger.info("Telegram bot polling started in dedicated thread.")
        try:
            self.bot.polling(none_stop=True)
        except Exception as e:
            logger.error(f"Error in Telegram polling thread: {e}", exc_info=True)
        logger.info("Telegram bot polling stopped.")

    async def receive(self, payload: Optional[dict] = None) -> dict: # Matches InterfaceBase
        """Получить запрос от пользователя (Telegram message), вернуть контекст."""
        # payload argument is ignored for Telegram as it polls.
        if payload:
            logger.debug("TG Interface: `receive` called with payload, but it's ignored for Telegram.")

        queued_payload = await self.message_queue.get() # This is the actual message from Telegram
        logger.debug(f"TG Interface: Dequeued message: {queued_payload}")

        chat_id = queued_payload["chat_id"]
        user_message_text = queued_payload.get("text", "") # Ensure text exists

        # History management:
        # The main loop will now manage history.
        # This receive method will provide the raw elements for history construction.
        # It should return a dict that process_user_message expects.
        # This includes chat_id for state lookup and the user's message.

        # The katana_states is now managed centrally or by process_user_message.
        # For now, let's assume process_user_message will handle history state.
        # This interface just delivers the message.

        # Return structure for process_user_message:
        # Needs to be consistent with what GemmaInterface.receive might return.
        return {
            "interface_type": "telegram", # To help process_user_message if needed
            "chat_id": chat_id,
            "user_id": queued_payload.get("user_id"),
            "text": user_message_text,
            # History is now managed by the main loop using the global 'chat_histories'.
            # This method provides the core message details.
            # "history": self.katana_states.get(chat_id, []).copy(), # REMOVED
            "raw_telegram_payload": queued_payload
        }

    async def send(self, response: dict) -> None: # Matches InterfaceBase
        """
        Отправить ответ пользователю Telegram.
        'response' dict is expected to contain 'chat_id' and 'text'.
        """
        chat_id = response.get("chat_id")
        response_text = response.get("text")

        if chat_id is None or response_text is None:
            logger.error(f"TG Interface: 'chat_id' or 'text' missing in response dict: {response}")
            return

        try:
            self.bot.send_message(chat_id, response_text)
            logger.info(f"TG Interface: Sent message to chat_id {chat_id}: {response_text}")

            # History update for assistant's response is now handled by process_user_message
            # or the main loop, which has access to the shared history state.
            # If self.katana_states is to be updated here, it needs careful synchronization
            # or be confirmed as the single source of truth managed by this class.
            # For now, assuming process_user_message updates the history it receives and returns it.
            # However, if TelegramInterface is solely responsible for its state:
            if chat_id in self.katana_states:
                 self.katana_states[chat_id].append({"role": "assistant", "content": response_text})
            else:
                 logger.warning(f"TG Interface: chat_id {chat_id} not in self.katana_states when attempting to log assistant response. This might be okay if history is managed externally.")

        except Exception as e:
            logger.error(f"TG Interface: Failed to send message to chat_id {chat_id}: {e}", exc_info=True)

    def stop_polling(self):
        """Stops the polling thread."""
        # telebot doesn't have a direct bot.stop_polling() for the thread version.
        # We rely on daemon=True and program exit, or more advanced signaling if needed.
        # For now, this is a placeholder if more graceful shutdown is required later.
        logger.info("TG Interface: stop_polling called (currently relies on daemon thread and program exit).")

# Example of how this might be used in main.py (conceptual)
async def main_loop_example():
    # This would come from env
    # TELEGRAM_TOKEN = os.getenv("KATANA_TELEGRAM_TOKEN")
    # if not TELEGRAM_TOKEN:
    #     print("KATANA_TELEGRAM_TOKEN not set.")
    #     return

    # tg_interface = TelegramInterface(api_token=TELEGRAM_TOKEN)

    # try:
    #     while True:
    #         # receive() now returns a dict including chat_id and history
    #         received_data = await tg_interface.receive()
    #         chat_id = received_data["chat_id"]

    #         # process_user_message would take the relevant parts of received_data
    #         # For example, just the text or the full history
    #         # Let's assume it needs a dict like {"text": "user message", "history": []}
    #         # and returns a dict like {"text": "bot response"}
    #         processing_payload = {
    #             "text": received_data["text"],
    #             "history": received_data["history"]
    #         }
    #         response_data = await process_user_message(processing_payload)

    #         await tg_interface.send(chat_id, response_data["text"])
    # except KeyboardInterrupt:
    #     logger.info("Main loop interrupted.")
    # finally:
    #     # tg_interface.stop_polling() # If implemented for graceful shutdown
    #     logger.info("Main loop finished.")

if __name__ == '__main__':
    # This is for standalone testing of TelegramInterface if needed
    # Requires KATANA_TELEGRAM_TOKEN to be set in environment

    # Basic logging for standalone test
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # loop = asyncio.get_event_loop()
    # try:
    #     loop.run_until_complete(main_loop_example())
    # except KeyboardInterrupt:
    #     logger.info("Test run interrupted.")
    pass
