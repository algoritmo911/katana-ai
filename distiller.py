import os
import openai
import asyncio
from typing import Tuple, List, Optional

# It's good practice to ensure the API key is loaded when this module is imported.
# The main bot.py script already calls load_dotenv(), so we can directly use os.environ.
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
else:
    print("[DISTILLER WARNING] OPENAI_API_KEY not found. Distillation and embedding will not work.")

# The prompt for the distillation model
DISTILLATION_PROMPT = """
You are a knowledge distillation assistant. Your task is to analyze the following conversation log and extract the key facts, entities, user intentions, and important decisions made.
Condense the dialogue into a structured, brief summary. The summary should be dense with information, focusing on conclusions, not the conversation's back-and-forth.
Present the output as a clean, concise text.

For example, if the conversation is:
User: "Hey, can you find me a good local plumber?"
Assistant: "Sure, I found one called 'Pipe Masters'. Their number is 555-1234. They have good reviews."
User: "Great, book them for tomorrow at 2 PM."
Assistant: "Okay, I've scheduled an appointment with Pipe Masters for tomorrow at 2 PM."

A good summary would be:
"An appointment was scheduled with the plumber 'Pipe Masters' (phone: 555-1234) for tomorrow at 2 PM at the user's request."

Now, analyze the following conversation:
---
{chat_history}
---
"""

async def distill_and_embed_conversation(chat_history: str) -> Optional[Tuple[str, List[float]]]:
    """
    Distills a conversation history into a summary and creates a vector embedding for it.

    Args:
        chat_history: A string containing the full conversation log.

    Returns:
        A tuple containing (summary_text, embedding_vector), or None if an error occurs.
    """
    if not OPENAI_API_KEY:
        print("[DISTILLER ERROR] Cannot distill conversation without OpenAI API key.")
        return None

    try:
        # Phase 1: The Distiller
        # Use asyncio.to_thread for the blocking OpenAI SDK call
        distillation_response = await asyncio.to_thread(
            openai.ChatCompletion.create,
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": DISTILLATION_PROMPT.format(chat_history=chat_history)}
            ]
        )
        summary_text = distillation_response.choices[0].message['content'].strip()

        if not summary_text:
            print("[DISTILLER INFO] Distillation resulted in an empty summary. Skipping embedding.")
            return None

        # Phase 2: The Semantic Encoder
        embedding_response = await asyncio.to_thread(
            openai.Embedding.create,
            input=summary_text,
            model="text-embedding-ada-002"
        )
        embedding_vector = embedding_response['data'][0]['embedding']

        print(f"[DISTILLER INFO] Successfully distilled and embedded conversation. Summary: '{summary_text[:100]}...'")
        return summary_text, embedding_vector

    except openai.APIError as e:
        print(f"[DISTILLER ERROR] OpenAI API error during distillation/embedding: {e}")
        return None
    except Exception as e:
        print(f"[DISTILLER ERROR] An unexpected error occurred in distill_and_embed_conversation: {e}")
        return None
