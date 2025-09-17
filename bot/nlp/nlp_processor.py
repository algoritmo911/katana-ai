import os
import json
import openai
from dotenv import load_dotenv
import functools

# Загружаем переменные окружения из .env файла
load_dotenv()

def _load_system_prompt():
    """Loads the system prompt from an external file."""
    try:
        with open(os.path.join(os.path.dirname(__file__), 'system_prompt.md'), 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print("ERROR: system_prompt.md not found. Using a default fallback prompt.")
        return "You are a helpful assistant. Respond in JSON."

class NLPError(Exception):
    """Кастомное исключение для ошибок NLP-процессора."""
    pass

class NLPProcessor:
    """
    Класс для обработки текста с использованием внешнего NLP-сервиса (OpenAI).
    Оптимизирован для удобства тестирования, конфигурации и производительности.
    """
    def __init__(self, api_key=None, model=None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY не найден и не был предоставлен.")

        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o")
        self.client = openai.OpenAI(api_key=self.api_key)
        self.system_prompt = _load_system_prompt()

    @functools.lru_cache(maxsize=128)
    def process_text(self, text: str, dialogue_history_json: str = None) -> dict:
        """
        Отправляет текст в OpenAI для анализа и возвращает структурированный JSON.
        Кэширует результаты для идентичных запросов.
        """
        dialogue_history = json.loads(dialogue_history_json) if dialogue_history_json else []

        messages = [{"role": "system", "content": self.system_prompt}]
        if dialogue_history:
            messages.extend(dialogue_history)
        messages.append({"role": "user", "content": text})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0,
                response_format={"type": "json_object"}
            )
            response_content = response.choices[0].message.content
            if not response_content:
                raise NLPError("OpenAI API вернул пустой ответ.")

            analysis_result = json.loads(response_content)
            return analysis_result

        except openai.APIError as e:
            raise NLPError(f"Ошибка API OpenAI: {e}")
        except json.JSONDecodeError:
            raise NLPError("Не удалось декодировать JSON из ответа OpenAI.")
        except Exception as e:
            raise NLPError(f"Непредвиденная ошибка в NLPProcessor: {e}")

# Пример использования
if __name__ == '__main__':
    try:
        processor = NLPProcessor()
        test_text_1 = "Найди мне данные по Sapiens Coin за прошлую неделю"
        print(f"--- Анализ 1: '{test_text_1}' ---")
        # Преобразуем историю в JSON-строку для кэширования
        history_json = json.dumps([
            {"role": "user", "content": "Предыдущий вопрос"},
            {"role": "assistant", "content": "Предыдущий ответ"},
        ])
        result_1 = processor.process_text(test_text_1, dialogue_history_json=history_json)
        print(json.dumps(result_1, indent=2, ensure_ascii=False))

        # Повторный вызов с теми же аргументами (должен быть взят из кэша)
        print("\n--- Повторный анализ (из кэша) ---")
        result_cached = processor.process_text(test_text_1, dialogue_history_json=history_json)
        print(json.dumps(result_cached, indent=2, ensure_ascii=False))

    except (ValueError, NLPError) as e:
        print(e)
