import openai
import json
from pydantic import ValidationError
from .models import IntentContract

class HypothesisGenerator:
    """
    Генерирует конкретный, машиночитаемый IntentContract из
    абстрактной проблемы.
    """
    def __init__(self):
        self.openai_client = openai.OpenAI()

    def generate_contract(self, problem_statement: str, max_retries: int = 3) -> IntentContract | None:
        """
        Генерирует и валидирует IntentContract.
        Включает цикл самокоррекции.
        """
        print(f"Генерация контракта для проблемы: '{problem_statement}'")

        # Получаем JSON-схему из Pydantic модели для включения в промпт
        schema_json = IntentContract.model_json_schema()

        system_prompt = (
            "You are a world-class Systems Architect and Project Manager. Your task is to convert an abstract strategic problem "
            "into a concrete, actionable, and machine-readable IntentContract. Your output MUST be a single, valid JSON object "
            "that strictly adheres to the provided JSON Schema. Do not add any extra text, comments, or explanations outside of the JSON structure."
        )

        # Начальный user_prompt
        user_prompt = (
            f"Please analyze the following strategic problem and generate an IntentContract based on it.\n\n"
            f"**Problem Statement:**\n\"{problem_statement}\"\n\n"
            f"**JSON Schema to follow:**\n```json\n{json.dumps(schema_json, indent=2)}\n```"
        )

        for attempt in range(max_retries):
            print(f"Попытка {attempt + 1}/{max_retries}...")

            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.2
                )

                response_json_str = response.choices[0].message.content
                response_data = json.loads(response_json_str)

                # Валидация с помощью Pydantic
                contract = IntentContract.model_validate(response_data)
                print("Контракт успешно сгенерирован и валидирован.")
                return contract

            except json.JSONDecodeError as e:
                print(f"Ошибка декодирования JSON: {e}. Повторная попытка...")
                user_prompt += f"\n\n[Correction] In the previous attempt, the output was not valid JSON. Error: {e}. Please ensure the output is a single, valid JSON object."

            except ValidationError as e:
                print(f"Ошибка валидации Pydantic: {e}. Повторная попытка...")
                user_prompt += f"\n\n[Correction] In the previous attempt, the JSON did not match the required schema. Validation errors: {e}. Please correct the structure and return a complete, valid JSON object."

            except Exception as e:
                print(f"Непредвиденная ошибка API: {e}. Повторная попытка...")

        print("Не удалось сгенерировать валидный контракт после нескольких попыток.")
        return None

# Пример использования
if __name__ == '__main__':
    # Убедитесь, что переменные окружения установлены
    generator = HypothesisGenerator()
    problem = "Проект 'Химера' отстает по срокам из-за нестабильности модуля компьютерного зрения."
    contract = generator.generate_contract(problem)

    if contract:
        print("\n--- Сгенерированный Контракт ---")
        print(contract.model_dump_json(indent=2, ensure_ascii=False))
    else:
        print("\nКонтракт не был сгенерирован.")
