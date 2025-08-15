import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Import the processors and the core
from src.processors import process_voice_message, process_video_note
from src.core import process_text_query

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# --- The Unified Pipeline Handler ---
async def pipeline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    This function is the single entry point for all messages. It acts as:
    1. The Unified Ingress
    2. The Triage Node
    3. The Egress Controller
    """
    message = update.message
    user_id = message.from_user.id if message.from_user else "Unknown"
    processed_text = None

    # 1. & 2. Unified Ingress & Triage Node
    # Determine modality and route to the correct processor
    if message.text:
        logger.info(f"Received TEXT message from user {user_id}")
        # TextProcessor is implicit: the text is already here.
        processed_text = message.text
    elif message.voice:
        logger.info(f"Received VOICE message from user {user_id}")
        processed_text = await process_voice_message(update)
    elif message.video_note:
        logger.info(f"Received VIDEO_NOTE message from user {user_id}")
        processed_text = await process_video_note(update)
    else:
        # This case should ideally not be hit due to the filters, but it's good practice
        logger.warning(f"Received an unsupported message type from user {user_id}")
        await message.reply_text("This message type is not supported yet.")
        return

    # If processing failed (e.g., transcription), the processor should have logged it
    # and returned None.
    if processed_text is None:
        logger.warning(f"Processing failed for a message from user {user_id}. No text to send to core.")
        return

    # 4. Cognitive Core
    # Send the processed text to the cognitive core
    logger.info(f"Sending to Cognitive Core: '{processed_text}'")
    response_text = await process_text_query(processed_text)

    # 5. Egress Controller
    # Send the core's response back to the user.
    # For now, all responses are text. In the future, this could use TTS for voice inputs.
    if response_text:
        logger.info(f"Sending response to user {user_id}: '{response_text}'")
        await message.reply_text(response_text)
    else:
        logger.error(f"Cognitive core returned no response for text: '{processed_text}'")
        await message.reply_text("I'm sorry, I couldn't come up with a response.")


# --- Main Application Setup ---
def main() -> None:
    """Start the bot."""
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("FATAL: TELEGRAM_BOT_TOKEN not found! Create a .env file and add your token.")
        return

    # Check for OpenAI key at startup to provide a clear warning if it's missing
    if not os.getenv("OPENAI_API_KEY"):
        logger.warning("WARNING: OPENAI_API_KEY not found! Voice and video processing will be disabled.")

    application = Application.builder().token(token).build()

    # The single handler for the entire pipeline, ignoring commands.
    # Commands can be handled by a separate CommandHandler if needed in the future.
    handler = MessageHandler(filters.TEXT | filters.VOICE | filters.VIDEO_NOTE & (~filters.COMMAND), pipeline_handler)
    application.add_handler(handler)

    logger.info("Katana is starting...")
    application.run_polling()
    logger.info("Katana has stopped.")

if __name__ == '__main__':
    main()
