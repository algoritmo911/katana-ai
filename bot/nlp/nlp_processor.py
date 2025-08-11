import os
import json
import openai
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

class NLPError(Exception):
    """Кастомное исключение для ошибок NLP-процессора."""
    pass

class NLPProcessor:
    """
    Класс для обработки текста с использованием внешнего NLP-сервиса (OpenAI).
    """
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY не найден в переменных окружения.")
        self.client = openai.OpenAI(api_key=self.api_key)

    def process_text(self, text: str) -> dict:
        """
        Отправляет текст в OpenAI для анализа и возвращает структурированный JSON.

        :param text: Текст для анализа.
        :return: Словарь с результатами анализа (entities, keywords, intent, sentiment).
        """
        system_prompt = """
        Ты - продвинутый NLP-процессор. Твоя задача - анализировать текст пользователя и возвращать ТОЛЬКО JSON-объект со следующей структурой:
        {
          "entities": [
            {"text": "...", "type": "PERSON"},
            {"text": "...", "type": "LOC"},
            {"text": "...", "type": "ORG"},
            {"text": "...", "type": "DATE"}
          ],
          "keywords": ["...", "..."],
          "intent": "...",
          "sentiment": "..."
        }
        - `entities`: Извлеки именованные сущности. Типы: PERSON, LOC (локация), ORG (организация), DATE.
        - `keywords`: Извлеки 5-7 ключевых слов или концепций из текста.
        - `intent`: Определи намерение пользователя. Варианты: "запрос информации", "постановка задачи", "планирование", "социальный диалог", "уточнение", "recall_information" (если пользователь спрашивает о чем-то, что он говорил ранее, например "куда я еду?", "с кем я встречаюсь?").
        - `sentiment`: Определи эмоциональную окраску: "positive", "negative", "neutral".
        - Если сущности не найдены, верни пустой список [].
        ВАЖНО: Твой ответ должен быть валидным JSON и ничего кроме него.
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )

            response_content = response.choices[0].message.content
            if not response_content:
                raise NLPError("OpenAI API вернул пустой ответ.")

            # Парсим JSON из ответа
            analysis_result = json.loads(response_content)
            return analysis_result

        except openai.APIError as e:
            # Обработка ошибок OpenAI
            raise NLPError(f"Ошибка API OpenAI: {e}")
        except json.JSONDecodeError:
            # Если OpenAI вернул невалидный JSON
            raise NLPError("Не удалось декодировать JSON из ответа OpenAI.")
        except Exception as e:
            # Прочие непредвиденные ошибки
            raise NLPError(f"Непредвиденная ошибка в NLPProcessor: {e}")

# Пример использования (для тестирования)
if __name__ == '__main__':
    # Убедитесь, что у вас есть файл .env с вашим OPENAI_API_KEY
    try:
        processor = NLPProcessor()
        test_text = "Планирую на следующей неделе деловую поездку в Берлин, нужно будет встретиться с Ангелой Меркель."
        result = processor.process_text(test_text)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (ValueError, NLPError) as e:
        print(e)
