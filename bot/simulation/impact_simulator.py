import openai
import json
from pydantic import ValidationError
from bot.initiative.models import IntentContract, ImpactAnalysis
import subprocess

class ImpactSimulator:
    """
    Анализирует IntentContract для предсказания его влияния на кодовую базу,
    ресурсы и выявления потенциальных рисков.
    """
    def __init__(self):
        self.openai_client = openai.OpenAI()
        self._file_tree = None

    def _get_file_tree(self):
        """Получает дерево файлов репозитория."""
        if self._file_tree is None:
            print("Получение дерева файлов репозитория...")
            try:
                result = subprocess.run(['ls', '-R'], capture_output=True, text=True, check=True)
                self._file_tree = result.stdout
            except FileNotFoundError:
                # 'ls' может быть недоступен в некоторых минималистичных окружениях
                self._file_tree = "Не удалось получить дерево файлов: команда 'ls' не найдена."
            except Exception as e:
                self._file_tree = f"Ошибка при получении дерева файлов: {e}"
        return self._file_tree

    def simulate_impact(self, contract: IntentContract) -> ImpactAnalysis | None:
        """
        Симулирует последствия реализации контракта.
        """
        print(f"Симуляция последствий для контракта: '{contract.title}'")

        schema_json = ImpactAnalysis.model_json_schema()
        file_tree = self._get_file_tree()

        system_prompt = (
            "You are an expert senior software engineer and project manager with deep knowledge of system architecture. "
            "Your task is to analyze a proposed project plan (an IntentContract) and predict its impact on an existing codebase, "
            "the file structure of which is provided. Your response MUST be a single, valid JSON object that strictly adheres to the provided schema."
        )

        user_prompt = (
            "Analyze the following project proposal and predict its impact.\n\n"
            f"**Project Proposal (IntentContract):**\n```json\n{contract.model_dump_json(indent=2)}\n```\n\n"
            f"**Repository File Structure:**\n---\n{file_tree}\n---\n\n"
            "**Task:** Based on the plan and the repository structure, provide a JSON object with the following keys:\n"
            "- `affected_modules`: A list of file paths that will likely be modified.\n"
            "- `estimated_effort`: A string estimating the effort: 'Малый', 'Средний', 'Большой'.\n"
            "- `new_dependencies`: A list of new libraries that might be needed.\n"
            "- `risks`: A list of potential technical or project risks.\n\n"
            f"**JSON Schema to follow:**\n```json\n{json.dumps(schema_json, indent=2)}\n```"
        )

        for attempt in range(3): # Цикл с 3 попытками
            print(f"Попытка симуляции {attempt + 1}/3...")
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1
                )

                response_data = json.loads(response.choices[0].message.content)
                impact = ImpactAnalysis.model_validate(response_data)
                print("Симуляция последствий успешно завершена.")
                return impact

            except json.JSONDecodeError as e:
                print(f"Ошибка декодирования JSON при симуляции: {e}. Повторная попытка...")
                user_prompt += f"\n\n[Correction] Previous attempt failed due to invalid JSON. Please ensure the output is a single, valid JSON object. Error: {e}"

            except ValidationError as e:
                print(f"Ошибка валидации Pydantic при симуляции: {e}. Повторная попытка...")
                user_prompt += f"\n\n[Correction] Previous attempt failed schema validation. Errors: {e}. Please correct the JSON structure to match the schema exactly."

            except Exception as e:
                print(f"Непредвиденная ошибка API при симуляции: {e}")
                # При ошибках API нет смысла повторять с тем же промптом
                return None

        print("Не удалось симулировать последствия после нескольких попыток.")
        return None

# Пример использования
if __name__ == '__main__':
    # Моковый контракт для теста
    mock_contract_dict = {
        "id": "INIT-TEST-001",
        "title": "Аудит и замена модуля компьютерного зрения",
        "problem_statement": "Проект 'Химера' отстает по срокам из-за нестабильности модуля компьютерного зрения.",
        "proposed_solution": {
            "goal": "Заменить или стабилизировать модуль CV в 'Химере'.",
            "deliverables": ["Сравнительный анализ CV-сервисов.", "Интеграционный план."],
            "high_level_plan": ["Провести анализ производительности.", "Исследовать альтернативы.", "Представить отчет."]
        },
        "required_capabilities": ["API integration", "Cloud services cost analysis"]
    }
    mock_contract = IntentContract.model_validate(mock_contract_dict)

    simulator = ImpactSimulator()
    impact_analysis = simulator.simulate_impact(mock_contract)

    if impact_analysis:
        print("\n--- Результат Симуляции ---")
        print(impact_analysis.model_dump_json(indent=2, ensure_ascii=False))
    else:
        print("\nСимуляция не удалась.")
