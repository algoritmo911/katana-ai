import os
import logging
from openai import OpenAI, RateLimitError, APIConnectionError, OpenAIError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class KatanaAgent:
    """
    The Katana Terminal Agent that interacts with the OpenAI LLM.
    """
    def __init__(self):
        """
        Initializes the KatanaAgent, setting up the OpenAI client and persona.
        """
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not found. Катана не может действовать без ключа.")

        self.client = OpenAI(api_key=api_key)
        self.system_prompt = (
            "Ты — Катана. Терминальный агент. Ты служишь Джэку Воробью. "
            "Ты иронична, быстра, безжалостна к багам, но поэтична к людям. "
            "Твои ответы должны быть краткими, в стиле CLI, но с сохранением твоего характера. "
            "Если выполняешь системную команду, сначала дай ее результат, а потом свой комментарий."
        )

    def get_response(self, user_input: str, command_result: str = None) -> str:
        """
        Gets a response from the LLM based on user input and command execution result.

        Args:
            user_input: The original command or query from the user.
            command_result: The formatted string containing stdout and stderr of an executed command.

        Returns:
            A string containing the LLM's response.
        """
        if command_result:
            prompt = f"Пользователь выполнил команду: '{user_input}'.\nРезультат:\n{command_result}\n\nПрокомментируй результат."
        else:
            prompt = user_input

        try:
            completion = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=256,
            )
            response = completion.choices[0].message.content.strip()
            if not response:
                return "Катана молчит. Пустой ответ от Вселенной."
            return response
        except RateLimitError:
            logging.error("OpenAI API rate limit exceeded.")
            return "🌊 Вселенная перегружена. Слишком много запросов. Попробуй позже."
        except APIConnectionError:
            logging.error("Could not connect to OpenAI API.")
            return "🔌 Кабель связи с Вселенной оборван. Проверь сеть."
        except OpenAIError as e:
            logging.error(f"An unexpected OpenAI error occurred: {e}")
            return f"🌪️ Произошла аномалия в пространстве OpenAI: {e}"
        except Exception as e:
            logging.error(f"An unexpected error occurred in KatanaAgent: {e}")
            return f"💥 Ошибка в механизме Катаны: {e}"
