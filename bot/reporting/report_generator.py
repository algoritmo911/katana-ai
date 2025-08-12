import json
import os
import networkx as nx
import openai

class ReportGenerator:
    """
    Генерирует финальный стратегический отчет на основе
    результатов анализа.
    """
    def __init__(self, output_dir="analysis_results"):
        self.openai_client = openai.OpenAI()
        self.output_dir = output_dir
        self.concepts = {}
        self.gap_analysis = {}
        self.graph = None
        self._load_data()

    def _load_data(self):
        """Загружает файлы с результатами анализа."""
        print("Загрузка результатов анализа...")
        try:
            with open(os.path.join(self.output_dir, "concepts.json"), 'r', encoding='utf-8') as f:
                self.concepts = json.load(f)

            with open(os.path.join(self.output_dir, "gap_analysis.json"), 'r', encoding='utf-8') as f:
                self.gap_analysis = json.load(f)

            graph_path = os.path.join(self.output_dir, "concept_graph.gml")
            if os.path.exists(graph_path):
                self.graph = nx.read_gml(graph_path)

            print("Данные для отчета успешно загружены.")
        except FileNotFoundError as e:
            print(f"Ошибка: Не найден файл с результатами анализа: {e}. Отчет не может быть создан.")
            raise
        except Exception as e:
            print(f"Ошибка при загрузке данных для отчета: {e}")
            raise

    def generate_mermaid_diagram(self):
        """Создает Mermaid-диаграмму из графа связей."""
        if not self.graph:
            return "Граф связей не был построен."

        print("Генерация Mermaid-диаграммы...")
        mermaid_string = "graph TD;\n"
        for node, data in self.graph.nodes(data=True):
            # Добавляем узел с его целью в виде всплывающей подсказки
            goal = data.get('goal', 'Цель не определена').replace('"', "'")
            mermaid_string += f'    {node}["{node}<br><small><i>{goal}</i></small>"];\n'

        for u, v, data in self.graph.edges(data=True):
            label = data.get('label', '')
            mermaid_string += f'    {u} -->|{label}| {v};\n'

        return f"```mermaid\n{mermaid_string}```\n"

    def _call_llm_for_synthesis(self, system_prompt, user_prompt_data, temperature=0.2):
        """Универсальная функция для вызова LLM для задач синтеза."""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt_data}
                ],
                temperature=temperature,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Ошибка при вызове LLM: {e}")
            return "Произошла ошибка при генерации этого раздела."

    def generate_executive_summary(self):
        """Генерирует исполнительное резюме с помощью LLM."""
        print("Генерация исполнительного резюме...")
        prompt = (
            "Напиши краткое, но емкое 'Исполнительное резюме' (Executive Summary) на основе следующих аналитических данных. "
            "Отрази общее состояние экосистемы проектов, ее главную цель и ключевые вызовы.\n\n"
            f"ДЕТАЛИ КОНЦЕПЦИЙ:\n{json.dumps(self.concepts, indent=2, ensure_ascii=False)}\n\n"
            f"РЕЗУЛЬТАТЫ GAP-АНАЛИЗА:\n{json.dumps(self.gap_analysis, indent=2, ensure_ascii=False)}"
        )
        system_prompt = "Ты - старший стратегический аналитик, готовящий отчет для CEO. Пиши в деловом, но ясном стиле."
        summary = self._call_llm_for_synthesis(system_prompt, prompt)
        return f"### Исполнительное Резюме\n\n{summary}"

    def generate_risk_opportunity_analysis(self):
        """Генерирует анализ рисков и возможностей с помощью LLM."""
        print("Генерация анализа рисков и возможностей...")
        prompt = (
            "На основе предоставленных данных о рисках проектов и результатах GAP-анализа, "
            "сформулируй ТОП-5 стратегических рисков и ТОП-5 стратегических возможностей для всей экосистемы. "
            "Риски - это не просто перечисление, а синтез, показывающий, как проблемы в одном проекте влияют на другие. "
            "Возможности - это неочевидные синергии или недооцененные направления, выявленные в 'белых пятнах'.\n\n"
            f"ДЕТАЛИ КОНЦЕПЦИЙ (обрати внимание на ключ 'risks'):\n{json.dumps(self.concepts, indent=2, ensure_ascii=False)}\n\n"
            f"РЕЗУЛЬТАТЫ GAP-АНАЛИЗА (используй 'gaps' и 'white_spots'):\n{json.dumps(self.gap_analysis, indent=2, ensure_ascii=False)}\n\n"
            "Отформатируй ответ строго в виде двух Markdown-списков."
        )
        system_prompt = "Ты - риск-менеджер и специалист по стратегическому развитию. Твоя задача - выявить самое важное."
        analysis = self._call_llm_for_synthesis(system_prompt, prompt, temperature=0.4)
        return f"### Анализ Рисков и Возможностей\n\n{analysis}"

    def generate_recommendations(self):
        """Генерирует стратегические рекомендации с помощью LLM."""
        print("Генерация стратегических рекомендаций...")
        prompt = (
            "Ты - главный стратег, и твоя задача - предложить следующие шаги. На основе ВСЕЙ представленной информации "
            "(детали концепций, GAP-анализ, риски и возможности), сформулируй 3 конкретные, приоритезированные и "
            "обоснованные рекомендации. Каждая рекомендация должна объяснять, какую проблему или возможность она решает "
            "и какой вклад вносит в глобальную цель.\n\n"
            f"ДЕТАЛИ КОНЦЕПЦИЙ:\n{json.dumps(self.concepts, indent=2, ensure_ascii=False)}\n\n"
            f"РЕЗУЛЬТАТЫ GAP-АНАЛИЗА:\n{json.dumps(self.gap_analysis, indent=2, ensure_ascii=False)}\n\n"
            "Отформатируй ответ в виде нумерованного Markdown-списка."
        )
        system_prompt = "Ты - главный стратег. Твои решения определяют будущее. Будь четок, конкретен и убедителен."
        recommendations = self._call_llm_for_synthesis(system_prompt, prompt, temperature=0.5)
        return f"### Рекомендации\n\n{recommendations}"

    def generate_full_report(self):
        """Собирает все части в единый Markdown отчет."""
        if not self.concepts:
            print("Нет данных для создания отчета.")
            return

        print("Сборка полного отчета...")
        report_parts = [
            "# State of the Noosphere, Q3 2025\n",
            self.generate_executive_summary(),
            "## Карта Проектов и Концепций\n",
            self.generate_mermaid_diagram(),
            self.generate_risk_opportunity_analysis(),
            self.generate_recommendations()
        ]

        full_report = "\n".join(report_parts)

        report_path = os.path.join(self.output_dir, "State_of_the_Noosphere_Q3_2025.md")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(full_report)

        print(f"Финальный отчет сохранен в: {report_path}")
        return full_report
