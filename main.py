import asyncio
import os
import logging
import json
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List

# --- Interface Imports ---
from src.interfaces.interface_base import InterfaceBase
from src.interfaces.telegram_interface import TelegramInterface
from src.interfaces.gemma_interface import GemmaInterface # Corrected class name if it was KodjimaInterface

# --- Bot Logic Imports (to be refactored from katana_bot) ---
# Placeholder: Actual NLP model call
async def get_katana_response_async(history: List[Dict[str, str]]) -> str:
    """Async placeholder for function getting response from NLP model."""
    logger.info(f"get_katana_response_async called with history: {history}")
    if not history:
        return "Katana is at your service. What shall we ponder?"

    # Simulate an async operation, e.g., an HTTP request to an LLM
    await asyncio.sleep(0.1)

    last_message = history[-1]['content']
    # This logic needs to be more sophisticated, actually calling an LLM
    return f"Pondering your last message: '{last_message}'... (this is an async placeholder)"

# --- Global State & Configuration ---
# Load .env file for environment variables
logger_main = logging.getLogger(__name__) # Logger for main.py
if load_dotenv():
    logger_main.info("✅ .env file loaded successfully.")
else:
    logger_main.warning("⚠️ .env file not found. Relying on system environment variables.")

# Configure logging (basic setup, can be enhanced)
log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
log_level = getattr(logging, log_level_str, logging.INFO)
logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Global chat histories object
# Key: chat_id (str or int), Value: list of messages [{'role': 'user'/'assistant', 'content': 'message_text'}]
chat_histories: Dict[Any, List[Dict[str, str]]] = {}

COMMAND_FILE_DIR = Path('commands')
COMMAND_FILE_DIR.mkdir(parents=True, exist_ok=True)

MESSAGE_ROLE_USER = "user"
MESSAGE_ROLE_ASSISTANT = "assistant"


# --- Core Message Processing Logic ---
async def process_user_message(payload: dict) -> dict:
    """
    Processes the user's message, manages history, and prepares a response.
    The 'payload' is what interface.receive() returns.
    It's expected to contain: 'chat_id', 'text', 'history', 'interface_type'.
    Returns a dictionary that the specific interface.send() method can understand.
    """
    interface_type = payload.get("interface_type", "unknown")
    chat_id = payload.get("chat_id") # Essential for state and Telegram
    user_message_text = payload.get("text", "")

    # Use history from payload (passed by interface.receive, originating from chat_histories)
    current_history = payload.get("history", [])

    logger_main.info(f"Processing message for chat_id {chat_id} via {interface_type}. Text: '{user_message_text}'")
    logger_main.debug(f"Incoming history for chat_id {chat_id}: {current_history}")

    # Add user's current message to history
    # (Interface.receive might have already done this if it maintains its own temporary state,
    # but this ensures it's part of the history being processed here)
    # Let's assume receive provides history *before* adding the current user message.
    current_history.append({"role": MESSAGE_ROLE_USER, "content": user_message_text})

    bot_response_text = ""
    is_command_response = False

    # 1. JSON Command Parsing (example: mind_clearing)
    try:
        parsed_json = json.loads(user_message_text)
        if isinstance(parsed_json, dict) and "type" in parsed_json:
            command_type = parsed_json.get("type")
            logger_main.info(f"Processing JSON command: type='{command_type}' for chat_id {chat_id}")

            if command_type == "mind_clearing":
                current_history = [] # Clear history
                bot_response_text = "✅ Context cleared. Starting fresh."
                # Add assistant's response to the now empty history
                current_history.append({"role": MESSAGE_ROLE_ASSISTANT, "content": bot_response_text})
                is_command_response = True
                logger_main.info(f"Mind clearing for chat_id {chat_id}. History reset.")
            # Add other JSON command handlers here (e.g., save_command)
            elif "module" in parsed_json and "args" in parsed_json and "id" in parsed_json: # Basic check for saveable command
                timestamp_str = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
                command_file_name = f"{timestamp_str}_{chat_id or 'unknown_chat'}.json"
                module_name = parsed_json.get('module', 'generic_module')

                # Use interface_type in path to distinguish commands from different sources
                module_command_dir = COMMAND_FILE_DIR / f"{interface_type}_mod_{module_name}"
                module_command_dir.mkdir(parents=True, exist_ok=True)
                command_file_path = module_command_dir / command_file_name

                with open(command_file_path, "w", encoding="utf-8") as f:
                    json.dump(parsed_json, f, ensure_ascii=False, indent=2)

                bot_response_text = f"✅ Command '{command_type}' received and saved to `{command_file_path}`."
                current_history.append({"role": MESSAGE_ROLE_ASSISTANT, "content": bot_response_text})
                is_command_response = True
                logger_main.info(f"Saved command from {chat_id} to {command_file_path}")
            else:
                logger_main.info(f"Unknown JSON command structure: {user_message_text}")
                # Fall through to treat as text or generate a specific "unknown command" response
    except json.JSONDecodeError:
        # Not a JSON command, proceed to natural language processing
        pass

    # 2. Natural Language Processing (if not a handled command)
    if not is_command_response:
        try:
            # This is where you'd call your actual LLM (e.g., Gemma, Anthropic, OpenAI)
            # The history already includes the current user message.
            katana_response_text = await get_katana_response_async(current_history)
            bot_response_text = katana_response_text
            current_history.append({"role": MESSAGE_ROLE_ASSISTANT, "content": bot_response_text})
        except Exception as e:
            error_id = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S_%f')
            logger_main.error(f"[ErrorID: {error_id}] Error during get_katana_response_async for chat_id {chat_id}: {e}", exc_info=True)
            bot_response_text = f"😕 Internal error processing your request (Ref: {error_id})."
            # Append error message to history as assistant's response
            current_history.append({"role": MESSAGE_ROLE_ASSISTANT, "content": bot_response_text})

    # Update global history state for this chat_id
    if chat_id:
        chat_histories[chat_id] = current_history
        logger_main.debug(f"Updated history for chat_id {chat_id}: {chat_histories[chat_id]}")


    # 3. Format response for the specific interface
    if interface_type == "telegram":
        return {"chat_id": chat_id, "text": bot_response_text}
    elif interface_type == "gemma":
        # GemmaInterface.send expects a dict to POST to the Kodjima API.
        # This dict should be structured according to Kodjima API requirements.
        # For example, if Kodjima expects a query in a specific format:
        # This is a placeholder structure. Replace with actual Kodjima API requirements.
        return {
            "query_to_kodjima": user_message_text, # Or a more processed version
            "user_context_for_kodjima": current_history, # If Kodjima API can take history
            "some_other_param": "value",
            # The actual bot_response_text (if GemmaInterface is just a passthrough to Kodjima API)
            # might not be used directly here if Kodjima itself generates the final user-facing text.
            # If process_user_message is meant to generate the request FOR Kodjima API based on user_message_text:
            "request_payload_for_gemma_api": { # This is what GemmaInterface.send will send
                 "userInput": user_message_text,
                 "history": current_history[:-1], # History without the last assistant response
                 "chatId": str(chat_id) if chat_id else None
            }
        }
    else: # Default or unknown interface
        logger_main.warning(f"Unknown interface type '{interface_type}' in process_user_message. Returning generic response.")
        return {"text": bot_response_text, "chat_id": chat_id, "error": "Interface type not fully supported for response formatting."}


# --- Main Application Loop ---
async def run(interface: InterfaceBase, initial_payload_for_gemma: Optional[dict] = None):
    logger_main.info(f"Bot starting with interface: {type(interface).__name__}")

    is_gemma_interface = isinstance(interface, GemmaInterface)

    if is_gemma_interface and initial_payload_for_gemma:
        # Single run for Gemma with initial payload
        logger_main.info(f"GemmaInterface: processing single initial payload: {initial_payload_for_gemma}")
        # GemmaInterface.receive expects a payload.
        # We need to populate 'chat_id' and 'history' if not present, or adapt.
        # For now, assume initial_payload_for_gemma is self-contained or GemmaInterface.receive handles it.
        # Let's ensure the initial_payload for Gemma includes a 'chat_id' for history tracking
        if 'chat_id' not in initial_payload_for_gemma:
            initial_payload_for_gemma['chat_id'] = initial_payload_for_gemma.get('user_id', 'gemma_default_chat') # Create a chat_id

        chat_id = initial_payload_for_gemma['chat_id']
        initial_payload_for_gemma['history'] = chat_histories.get(chat_id, []).copy()
        initial_payload_for_gemma['interface_type'] = 'gemma'


        received_payload = await interface.receive(initial_payload_for_gemma) # Pass the CLI/initial payload

        # Check if 'history' is in received_payload, if not, fetch from global
        if 'history' not in received_payload and chat_id in chat_histories:
             received_payload['history'] = chat_histories[chat_id].copy()
        elif 'history' not in received_payload:
             received_payload['history'] = []

        if 'chat_id' not in received_payload: # Ensure chat_id from interface.receive() if it modifies it
            received_payload['chat_id'] = chat_id


        response_for_send = await process_user_message(received_payload)

        # For Gemma, the response_for_send is the dict to be sent to Kodjima API
        # The 'send' method of GemmaInterface takes this dict directly.
        await interface.send(response_for_send['request_payload_for_gemma_api']) # Send the specific part
        logger_main.info("GemmaInterface: Sent request to Kodjima API. Output (if any) from Kodjima is logged by GemmaInterface.")
        # The current GemmaInterface.send does not return Kodjima's response to this loop.
        # This needs to be addressed if we want to show Kodjima's output to the user here.
        return # End after single run

    # Continuous loop for polling interfaces like Telegram
    while True:
        try:
            # For Telegram, `receive` ignores payload and waits on its internal queue.
            # For Gemma (if it were polling, which it's not here), it would need different handling.
            received_payload = await interface.receive() # No payload for polling interfaces

            # Ensure history is correctly populated from global state into the payload
            # that process_user_message will use.
            # TelegramInterface.receive already includes 'history' and 'chat_id'.

            chat_id = received_payload.get("chat_id")
            if chat_id and chat_id not in chat_histories:
                chat_histories[chat_id] = []

            # If interface.receive() doesn't provide history, or we want to ensure it's from global store:
            # received_payload['history'] = chat_histories.get(chat_id, []).copy()
            # The current TelegramInterface.receive *does* provide history from its own katana_states.
            # This might lead to divergence if chat_histories here is the source of truth.
            # Decision: Interfaces should fetch history from this global `chat_histories` via the payload from `receive`.
            # So, TelegramInterface.receive needs to be adjusted to NOT use its own self.katana_states for the outgoing history.
            # It should return the message, and the main loop adds history.
            # OR, TelegramInterface.receive adds user message to history it gets from global.

            # Let's refine:
            # 1. Interface.receive gets message, identifies chat_id, text.
            # 2. Main loop prepares payload for process_user_message: {chat_id, text, history_from_global_chat_histories, interface_type}
            # This means modifying interface.receive's return slightly.

            # Current TelegramInterface.receive returns:
            # { "interface_type": "telegram", "chat_id": chat_id, "user_id": ..., "text": ...,
            #   "history": self.katana_states.get(chat_id, []).copy(), ... }
            # This is problematic if self.katana_states in TelegramInterface is different from global chat_histories.
            # For consistency, interfaces should not manage history long-term.
            # The global `chat_histories` here is the source of truth.
            # `TelegramInterface.receive` can return a payload without history.
            # The main loop then adds the correct history from `chat_histories`.

            # Corrected flow for main loop:
            raw_from_interface = await interface.receive()
            chat_id = raw_from_interface.get("chat_id")

            if chat_id and chat_id not in chat_histories: # Initialize history for new chat_id
                chat_histories[chat_id] = []

            processing_payload = {
                **raw_from_interface, # Contains text, chat_id, interface_type
                "history": chat_histories.get(chat_id, []).copy() # Add authoritative history
            }

            response_data = await process_user_message(processing_payload)

            # `response_data` is now formatted by `process_user_message` specifically
            # for the target interface's `send` method.
            await interface.send(response_data)

        except asyncio.CancelledError:
            logger_main.info("Main loop cancelled. Shutting down.")
            break
        except Exception as e:
            logger_main.error(f"Error in main loop: {e}", exc_info=True)
            # Avoid busy-looping on persistent errors
            await asyncio.sleep(5)


# --- Entry Point ---
if __name__ == "__main__":
    # Determine which interface to use
    interface_choice = os.getenv("INTERFACE", "telegram").lower()
    selected_interface: Optional[InterfaceBase] = None
    gemma_initial_payload_dict: Optional[dict] = None

    logger_main.info(f"INTERFACE environment variable set to: '{interface_choice}'")

    if interface_choice == "telegram":
        TELEGRAM_TOKEN = os.getenv("KATANA_TELEGRAM_TOKEN")
        if not TELEGRAM_TOKEN:
            logger_main.error("❌ KATANA_TELEGRAM_TOKEN environment variable not set for Telegram interface.")
            exit(1)
        selected_interface = TelegramInterface(api_token=TELEGRAM_TOKEN)
        # Telegram specific: start heartbeat (if this logic is to be kept from katana_bot)
        # from bot.katana_bot import start_heartbeat_thread, stop_heartbeat_thread
        # start_heartbeat_thread() # This would need katana_bot.py to be importable and setup
        logger_main.info("Using Telegram interface.")

    elif interface_choice == "gemma":
        GEMMA_API_KEY = os.getenv("GEMMA_API_KEY")
        if not GEMMA_API_KEY:
            logger_main.error("❌ GEMMA_API_KEY environment variable not set for Gemma interface.")
            exit(1)
        selected_interface = GemmaInterface(api_key=GEMMA_API_KEY)
        logger_main.info("Using Gemma interface (for single shot execution via Kodjima API).")

        # For Gemma, we expect a JSON payload from stdin or a file for a single run.
        # Example: echo '{"text": "Hello Gemma", "user_id": "cli_user_1"}' | python main.py
        # This part needs to be properly implemented if CLI JSON input is desired.
        # For now, using a hardcoded example payload for testing the Gemma path.
        # This should ideally come from sys.argv or a dedicated CLI argument parser.
        gemma_test_payload_str = os.getenv("GEMMA_PAYLOAD_JSON")
        if gemma_test_payload_str:
            try:
                gemma_initial_payload_dict = json.loads(gemma_test_payload_str)
                logger_main.info(f"Loaded GEMMA_PAYLOAD_JSON: {gemma_initial_payload_dict}")
            except json.JSONDecodeError:
                logger_main.error(f"Failed to parse GEMMA_PAYLOAD_JSON: {gemma_test_payload_str}")
                exit(1)
        else:
            # Default test payload if nothing is provided
            gemma_initial_payload_dict = {"text": "Test message for Gemma API via main.py", "user_id": "test_user_main_py"}
            logger_main.info(f"GEMMA_PAYLOAD_JSON not set, using default test payload: {gemma_initial_payload_dict}")

    else:
        logger_main.error(f"❌ Unknown interface choice: '{interface_choice}'. Supported: telegram, gemma.")
        exit(1)

    # Run the main application loop
    main_event_loop = asyncio.get_event_loop()
    try:
        main_event_loop.run_until_complete(run(selected_interface, gemma_initial_payload_dict))
    except KeyboardInterrupt:
        logger_main.info("🤖 Application interrupted by user (Ctrl+C). Shutting down...")
    except Exception as e:
        logger_main.error(f"💥 An unexpected error occurred at the top level: {e}", exc_info=True)
    finally:
        logger_main.info("Initiating shutdown sequence...")
        # if interface_choice == "telegram":
            # stop_heartbeat_thread() # Ensure graceful shutdown of heartbeat
        # Add any other cleanup needed
        # Close asyncio loop
        # Gather all pending tasks and cancel them
        pending = asyncio.all_tasks(loop=main_event_loop)
        for task in pending:
            task.cancel()
        if pending:
            main_event_loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

        main_event_loop.close()
        logger_main.info("🛑 Application has shut down.")
