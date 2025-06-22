import os
import logging
from anthropic import Anthropic, APIError, AuthenticationError, BadRequestError, RateLimitError

from .base_nlp_client import NLPAuthenticationError, NLPBadRequestError, NLPRateLimitError, NLPAPIError, NLPTimeoutError, NLPServiceError

# Configure basic logging if not configured by the application root
# For a library, it's often better to just get the logger and let the application configure handlers
logger = logging.getLogger(__name__)
if not logger.hasHandlers(): # Avoid adding multiple handlers if already configured
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')


ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not ANTHROPIC_API_KEY:
    logger.warning("ANTHROPIC_API_KEY environment variable not set at module load time. Anthropic client calls will fail if not set by runtime.")

def get_anthropic_chat_response(history: list, user_prompt: str, model_name: str = "claude-3-opus-20240229", max_tokens_to_sample: int = 1024, system_prompt: str = None) -> str:
    """
    Gets a chat response from the Anthropic API.

    Args:
        history: A list of previous messages in the conversation.
                 Each message should be a dict with "role" ("user" or "assistant") and "content" keys.
                 Example: [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi there!"}]
                 Messages must alternate between user and assistant roles.
        user_prompt: The user's current prompt.
        model_name: The name of the Anthropic model to use.
        max_tokens_to_sample: The maximum number of tokens to generate in the response.
        system_prompt: An optional system prompt to guide the model's behavior.

    Returns:
        The assistant's response message content.

    Raises:
        ValueError: If the API key is not set, or if message history is not valid (client-side checks).
        NLPAuthenticationError: For API key authentication issues with the Anthropic service.
        NLPBadRequestError: For invalid requests sent to Anthropic (e.g., malformed messages, role sequence issues detected by the API).
        NLPRateLimitError: For exceeding Anthropic API rate limits.
        NLPAPIError: For other API related errors from Anthropic.
        NLPServiceError: For unexpected errors during the process or unhandled API errors.
    """
    if not ANTHROPIC_API_KEY:
        logger.error("Anthropic API key (ANTHROPIC_API_KEY) is not configured.")
        raise ValueError("Anthropic API key is not configured. Please set the ANTHROPIC_API_KEY environment variable.")

    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    messages = []
    # Validate and build messages from history
    last_role = None
    for i, msg in enumerate(history):
        if isinstance(msg, dict) and msg.get("role") in ["user", "assistant"] and "content" in msg:
            current_role = msg["role"]
            # Ensure alternating roles
            if last_role and last_role == current_role:
                err_msg = f"Invalid message history: Message {i} has role '{current_role}' which is same as previous. Roles must alternate."
                logger.error(err_msg)
                raise ValueError(err_msg)
            messages.append({"role": current_role, "content": msg["content"]})
            last_role = current_role
        else:
            logger.warning(f"Skipping invalid message in history due to format or role: {msg}")
            # Potentially raise ValueError here if strict validation is required for all history items

    # Add the current user prompt
    if last_role == "user":
        err_msg = "Invalid message sequence: The last message in history is from 'user'. New user_prompt cannot follow a 'user' message."
        logger.error(err_msg)
        raise ValueError(err_msg)

    messages.append({"role": "user", "content": user_prompt})

    # Anthropic API requires the first message to be 'user' if history is empty.
    if not messages: # Should not happen if user_prompt is always added, but as a safeguard
        err_msg = "Message list cannot be empty."
        logger.error(err_msg)
        raise ValueError(err_msg)
    if messages[0]["role"] == "assistant":
        err_msg = "Invalid message sequence: The first message in the list cannot be from 'assistant'."
        logger.error(err_msg)
        # This could happen if history starts with assistant and user_prompt is the first user message.
        # Depending on strictness, one might prepend a dummy user message or raise.
        # For now, raising error. A common pattern is: user, assistant, user, assistant, ...
        raise ValueError(err_msg)


    try:
        api_params = {
            "model": model_name,
            "max_tokens": max_tokens_to_sample,
            "messages": messages
        }
        if system_prompt:
            api_params["system"] = system_prompt

        logger.info(f"Sending request to Anthropic API. Model: {model_name}. System prompt used: {bool(system_prompt)}. Number of messages: {len(messages)}.")
        # For debugging, be cautious about logging full messages if they contain sensitive PII.
        # logger.debug(f"Anthropic request messages: {json.dumps(messages, indent=2)}")


        response = client.messages.create(**api_params)

        if not response.content or not hasattr(response.content[0], 'text') or not response.content[0].text:
            err_msg = "Anthropic API response content is empty or not in expected format."
            logger.error(err_msg)
            # Use original_error=None as this is a client-side observation of the response structure
            raise NLPAPIError(message=err_msg, original_error=None, user_message="Ответ от NLP сервиса (Anthropic) был получен в неожиданном формате.")

        assistant_response = response.content[0].text
        logger.info(f"Received response from Anthropic API. Model: {response.model}. Output Tokens: {response.usage.output_tokens}. Input Tokens: {response.usage.input_tokens}. Stop Reason: {response.stop_reason}")
        return assistant_response

    except AuthenticationError as e:
        error_msg_log = f"Anthropic API AuthenticationError (Status {e.status_code}): {e.body.get('error', {}).get('message', str(e)) if e.body else str(e)}"
        logger.error(error_msg_log)
        raise NLPAuthenticationError(message=error_msg_log, original_error=e) from e
    except BadRequestError as e:
        error_detail = str(e)
        if e.body and 'error' in e.body and 'message' in e.body['error']:
            error_detail = e.body['error']['message']
        error_msg_log = f"Anthropic API BadRequestError (Status {e.status_code}): {error_detail}"
        logger.error(error_msg_log)
        # User message might need to be more specific if we can parse the error_detail
        user_msg = "Ошибка в запросе к NLP сервису (Anthropic). Проверьте формат данных или обратитесь к логам."
        if "alternating user/assistant" in error_detail.lower():
            user_msg = "Ошибка в последовательности сообщений для NLP сервиса (Anthropic). Роли должны чередоваться."
        raise NLPBadRequestError(message=error_msg_log, original_error=e, user_message=user_msg) from e
    except RateLimitError as e:
        error_msg_log = f"Anthropic API RateLimitError (Status {e.status_code}): {e.body.get('error', {}).get('message', str(e)) if e.body else str(e)}"
        logger.error(error_msg_log)
        raise NLPRateLimitError(message=error_msg_log, original_error=e) from e
    except APIError as e: # Catch other specific Anthropic APIErrors
        error_message_detail = str(e)
        if hasattr(e, 'body') and e.body and 'error' in e.body and 'message' in e.body['error']:
            error_message_detail = e.body['error']['message']
        error_msg_log = f"Anthropic APIError (Status {e.status_code if hasattr(e, 'status_code') else 'N/A'}): {error_message_detail}"
        logger.error(error_msg_log)
        raise NLPAPIError(message=error_msg_log, original_error=e) from e
    except Exception as e: # Catch any other unexpected errors (network issues, etc.)
        error_msg_log = f"An unexpected error occurred while calling Anthropic API: {str(e)}"
        logger.error(error_msg_log, exc_info=True)
        # For truly unexpected errors, a generic user message is appropriate.
        raise NLPServiceError(message=error_msg_log, original_error=e) from e
