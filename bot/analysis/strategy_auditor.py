import json
import openai

class StrategyAuditor:
    """
    Выполняет GAP-анализ на основе данных, извлеченных ConceptAnalyzer.
    """
    def __init__(self, concept_details, all_documents_text):
        self.openai_client = openai.OpenAI()
        self.concept_details = concept_details
        self.full_context = all_documents_text
        self.analysis_results = {}

    def perform_gap_analysis(self):
        """
        Запускает LLM для выполнения GAP-анализа.
        """
        print("Начинаю GAP-анализ...")

        system_prompt = (
            "Ты - стратегический аналитик мирового класса. Твоя задача - провести GAP-анализ портфеля "
            "взаимосвязанных проектов. На основе предоставленных структурированных данных о каждом проекте "
            "(цели, статус, риски) и полного контекста всех доступных документов, определи ключевые "
            "стратегические идеи. Твой ответ должен быть единым JSON-объектом со следующими ключами: "
            "'gaps', 'white_spots', 'contradictions'."
        )

        user_prompt = (
            "Вот данные для анализа:\n\n"
            f"**СТРУКТУРИРОВАННЫЕ ДАННЫЕ О КОНЦЕПЦИЯХ:**\n```json\n{json.dumps(self.concept_details, indent=2, ensure_ascii=False)}\n```\n\n"
            f"**ПОЛНЫЙ КОНТЕКСТ ИЗ ВСЕХ ДОКУМЕНТОВ:**\n---\n{self.full_context}\n---\n\n"
            "**ЗАДАНИЕ:**\n"
            "1.  **'gaps'**: Перечисли области, где заявленная 'цель' проекта значительно отличается от его "
            "текущего 'статуса'. Укажи проекты, которые отстают или чей прогресс не соответствует целям.\n"
            "2.  **'white_spots'**: Определи важные стратегические области или возможности, которые необходимы "
            "для достижения глобальной цели (например, 'Атлант' или 'Ноосфера'), но в настоящее время не "
            "покрыты ни одним из описанных проектов.\n"
            "3.  **'contradictions'**: Найди любые противоречия между проектами, их целями или рисками. "
            "Например, создает ли цель одного проекта риск для другого?\n\n"
            "Предоставь результат в виде JSON."
        )

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1, # Немного креативности для анализа
            )
            analysis = response.choices[0].message.content
            self.analysis_results = json.loads(analysis)
            print("GAP-анализ успешно завершен.")
            return self.analysis_results
        except Exception as e:
            print(f"Ошибка во время GAP-анализа: {e}")
            return None
