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

    def process_text(self, text: str, dialogue_history: list[dict] = None) -> dict:
        """
        Отправляет текст в OpenAI для анализа и возвращает структурированный JSON.

        :param text: Текст для анализа.
        :param dialogue_history: Список предыдущих сообщений для контекста.
        :return: Словарь с результатами анализа.
        """
        system_prompt = """
        Ты — "Когнитивное Ядро" для ИИ-ассистента "Katana". Твоя задача — глубокий семантический анализ входящих запросов.
        Возвращай ТОЛЬКО JSON-объект со следующей структурой:
        {
          "intent": "...",
          "entities": [
            {"text": "...", "type": "document_name"},
            {"text": "...", "type": "time_range"},
            {"text": "...", "type": "person"},
            {"text": "...", "type": "location"},
            {"text": "...", "type": "organization"},
            {"text": "...", "type": "date"}
          ],
          "keywords": ["...", "..."],
          "sentiment": "...",
          "dialogue_state": "..."
        }

        ### Описание полей:
        1.  **`intent`**: Определи основное намерение пользователя. Варианты:
            *   `search_documents`: Поиск документов или данных. Пример: "Найди мне данные по Sapiens Coin за прошлую неделю".
            *   `get_weather`: Запрос погоды.
            *   `tell_joke`: Просьба рассказать шутку.
            *   `greeting`: Приветствие.
            *   `goodbye`: Прощание.
            *   `get_time`: Запрос времени.
            *   `recall_information`: Пользователь просит вспомнить что-то из предыдущего контекста. Пример: "О чем мы только что говорили?".
            *   `clarification`: Ответ пользователя на уточняющий вопрос от бота.
            *   `fallback_general`: Если намерение неясно.

        2.  **`entities`**: Извлеки именованные сущности.
            *   `document_name`: Название документа, файла, отчета. Пример: "Sapiens Coin", "отчет по Q3".
            *   `time_range`: Временной диапазон. Пример: "за прошлую неделю", "вчера", "с 1 по 5 мая".
            *   `person`: Имя и/или фамилия.
            *   `location`: Географическое место.
            *   `organization`: Название компании или организации.
            *   `date`: Конкретная дата или день.

        3.  **`keywords`**: Извлеки 5-7 ключевых слов или концепций.

        4.  **`sentiment`**: Определи окраску: "positive", "negative", "neutral".

        5.  **`dialogue_state`**: Определи состояние диалога.
            *   `new_request`: Новый, независимый запрос.
            *   `continuation`: Продолжение предыдущего запроса. Пример: "А теперь отсортируй по дате".
            *   `clarification_response`: Ответ на прямой вопрос от бота.

        ### Правила:
        - Если сущности не найдены, верни пустой список `[]`.
        - Твой ответ должен быть валидным JSON и ничего кроме него.
        - Анализируй `dialogue_history` для определения `dialogue_state`. Если `dialogue_history` пуст, то это `new_request`.
        """

        messages = [{"role": "system", "content": system_prompt}]
        if dialogue_history:
            messages.extend(dialogue_history)
        messages.append({"role": "user", "content": text})

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
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
        result_1 = processor.process_text(test_text_1)
        print(json.dumps(result_1, indent=2, ensure_ascii=False))

        # Эмуляция истории для второго запроса
        history = [
            {"role": "user", "content": test_text_1},
            {"role": "assistant", "content": "Вот данные по Sapiens Coin..."},
        ]
        test_text_2 = "А теперь отсортируй по дате"
        print(f"\n--- Анализ 2: '{test_text_2}' (с контекстом) ---")
        result_2 = processor.process_text(test_text_2, dialogue_history=history)
        print(json.dumps(result_2, indent=2, ensure_ascii=False))

    except (ValueError, NLPError) as e:
        print(e)
