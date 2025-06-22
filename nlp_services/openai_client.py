# Placeholder for OpenAI client logic
import os
import logging

from openai import OpenAI, APIError, AuthenticationError, BadRequestError, RateLimitError as OpenAIClientRateLimitError # Alias to avoid clash if needed later
from .base_nlp_client import NLPAuthenticationError, NLPBadRequestError, NLPRateLimitError, NLPAPIError, NLPServiceError # Import custom exceptions

# Configure basic logging if not configured by the application root
logger = logging.getLogger(__name__)
if not logger.hasHandlers(): # Avoid adding multiple handlers if already configured
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY environment variable not set at module load time. OpenAI client calls will fail if not set by runtime.")

def get_openai_chat_response(history: list, user_prompt: str, model_name: str = "gpt-3.5-turbo", system_prompt: str = None, max_tokens: int = 1024) -> str:
    """
    Gets a chat response from the OpenAI API using Chat Completions.

    Args:
        history: A list of previous messages in the conversation.
                 Each message should be a dict with "role" ("system", "user", or "assistant")
                 and "content" keys.
                 Example: [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi there!"}]
        user_prompt: The user's current prompt.
        model_name: The name of the OpenAI model to use.
        system_prompt: An optional system prompt to guide the model's behavior.
                       If provided, it will be prepended to the messages list with role "system".
        max_tokens: The maximum number of tokens to generate in the response.

    Returns:
        The assistant's response message content.

    Raises:
        ValueError: If the API key is not set (client-side check).
        NLPAuthenticationError: For API key authentication issues with OpenAI.
        NLPBadRequestError: For invalid requests sent to OpenAI (e.g., malformed messages).
        NLPRateLimitError: For exceeding OpenAI API rate limits.
        NLPAPIError: For other API related errors from OpenAI.
        NLPServiceError: For unexpected errors during the process or unhandled API errors.
    """
    if not OPENAI_API_KEY:
        logger.error("OpenAI API key (OPENAI_API_KEY) is not configured.")
        raise ValueError("OpenAI API key is not configured. Please set the OPENAI_API_KEY environment variable.")

    client = OpenAI(api_key=OPENAI_API_KEY)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    # Add history messages
    # Basic validation: ensure role and content exist. More specific validation (e.g. role order)
    # is often handled by the OpenAI API itself, but can be added here if needed.
    for msg in history:
        if isinstance(msg, dict) and msg.get("role") in ["system", "user", "assistant"] and "content" in msg:
            messages.append({"role": msg["role"], "content": msg["content"]})
        else:
            logger.warning(f"Skipping invalid message in history for OpenAI: {msg}")
            # Consider raising ValueError for critical format issues if necessary

    messages.append({"role": "user", "content": user_prompt})

    try:
        logger.info(f"Sending request to OpenAI API. Model: {model_name}. System prompt used: {bool(system_prompt)}. Number of messages: {len(messages)}.")
        # logger.debug(f"OpenAI request messages: {messages}") # Be cautious with logging full prompts

        chat_completion = client.chat.completions.create(
            model=model_name,
            messages=messages,
            max_tokens=max_tokens
        )

        # Ensure response and choices are valid
        if not chat_completion.choices or not hasattr(chat_completion.choices[0], 'message') or not chat_completion.choices[0].message:
            err_msg = "OpenAI API response is empty or not in expected format (no choices or message)."
            logger.error(err_msg)
            raise NLPAPIError(message=err_msg, original_error=None, user_message="Ответ от NLP сервиса (OpenAI) был получен в неожиданном формате.")

        assistant_response = chat_completion.choices[0].message.content

        if assistant_response is None: # Should ideally be caught by the above if message object is missing, but good explicit check
            err_msg = "OpenAI API response message content is None."
            logger.error(err_msg)
            raise NLPAPIError(message=err_msg, original_error=None, user_message="Ответ от NLP сервиса (OpenAI) не содержит текстового ответа.")

        # Log token usage if available (depends on OpenAI library version and response structure)
        input_tokens = chat_completion.usage.prompt_tokens if chat_completion.usage else 'N/A'
        output_tokens = chat_completion.usage.completion_tokens if chat_completion.usage else 'N/A'

        logger.info(f"Received response from OpenAI API. Model: {chat_completion.model}. Output Tokens: {output_tokens}. Input Tokens: {input_tokens}. Finish Reason: {chat_completion.choices[0].finish_reason}")
        return assistant_response

    except AuthenticationError as e:
        error_msg_log = f"OpenAI API AuthenticationError: {e}"
        logger.error(error_msg_log)
        raise NLPAuthenticationError(message=error_msg_log, original_error=e, user_message="Ошибка аутентификации с OpenAI. Проверьте API ключ.") from e
    except BadRequestError as e: # Specific OpenAI error for malformed requests etc.
        error_msg_log = f"OpenAI API BadRequestError: {e}" # e.g. invalid model, bad parameters
        logger.error(error_msg_log)
        # Try to get more specific info if available in e.response.json().get('error', {}).get('message')
        user_msg = "Ошибка в запросе к NLP сервису (OpenAI). Проверьте формат данных или параметры запроса."
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                api_err_msg = error_data.get('error', {}).get('message', '')
                if api_err_msg:
                    error_msg_log += f" | API Message: {api_err_msg}" # Append to technical log
                    # Potentially refine user_msg based on api_err_msg if common patterns emerge
            except Exception: # JSONDecodeError or other issues
                pass # Stick to default user_msg
        raise NLPBadRequestError(message=error_msg_log, original_error=e, user_message=user_msg) from e
    except OpenAIClientRateLimitError as e: # Using aliased import
        error_msg_log = f"OpenAI API RateLimitError: {e}"
        logger.error(error_msg_log)
        raise NLPRateLimitError(message=error_msg_log, original_error=e, user_message="Превышен лимит запросов к OpenAI. Пожалуйста, попробуйте позже.") from e
    except APIError as e: # Generic OpenAI API error
        error_msg_log = f"OpenAI API generic APIError: {e}"
        logger.error(error_msg_log)
        raise NLPAPIError(message=error_msg_log, original_error=e, user_message="Произошла непредвиденная ошибка при работе с OpenAI API.") from e
    except Exception as e: # Other unexpected errors (e.g. network issues not caught by httpx within OpenAI client)
        error_msg_log = f"An unexpected error occurred while calling OpenAI API: {str(e)}"
        logger.error(error_msg_log, exc_info=True)
        raise NLPServiceError(message=error_msg_log, original_error=e) from e
