import os
import json
import networkx as nx
from bot.analysis.concept_analyzer import ConceptAnalyzer
from bot.analysis.strategy_auditor import StrategyAuditor
from bot.reporting.report_generator import ReportGenerator

def main():
    """
    Основная функция для запуска полного процесса анализа.
    """
    # Вручную устанавливаем переменные окружения для этого скрипта
    os.environ["OPENAI_API_KEY"] = "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"
    os.environ["SUPABASE_KEY"] = "sb_secret_wtRSbhoCKkW53FAn2UzFpg_ED78K1LU"
    os.environ["SUPABASE_URL"] = "https://pmcaojgdrszvujvwzxrc.supabase.co"

    output_dir = "analysis_results"
    os.makedirs(output_dir, exist_ok=True)

    # --- Слой 2: Анализ Концепций ---
    print("--- Запуск Слой 2: ConceptAnalyzer ---")
    analyzer = ConceptAnalyzer()
    analyzer.run_analysis()

    # Сохранение результатов анализа концепций
    details_path = os.path.join(output_dir, "concepts.json")
    if analyzer.concept_details:
        with open(details_path, 'w', encoding='utf-8') as f:
            json.dump(analyzer.concept_details, f, ensure_ascii=False, indent=2)
        print(f"Детали концепций сохранены в: {details_path}")
    else:
        print("Детали концепций не были извлечены. Анализ не может продолжаться.")
        return

    graph_path = os.path.join(output_dir, "concept_graph.gml")
    if analyzer.graph and analyzer.graph.nodes:
        nx.write_gml(analyzer.graph, graph_path)
        print(f"Граф связей сохранен в: {graph_path}")
    else:
        print("Граф связей не был построен.")

    print("--- Слой 2 завершен. ---\n")

    # --- Слой 3: GAP-Анализ ---
    print("--- Запуск Слой 3: StrategyAuditor ---")
    # Собираем весь текст для полного контекста
    full_text_context = "\n\n".join([doc['content'] for doc in analyzer.documents])

    auditor = StrategyAuditor(
        concept_details=analyzer.concept_details,
        all_documents_text=full_text_context
    )
    gap_analysis_results = auditor.perform_gap_analysis()

    # Сохранение результатов GAP-анализа
    gap_analysis_path = os.path.join(output_dir, "gap_analysis.json")
    if gap_analysis_results:
        with open(gap_analysis_path, 'w', encoding='utf-8') as f:
            json.dump(gap_analysis_results, f, ensure_ascii=False, indent=2)
        print(f"Результаты GAP-анализа сохранены в: {gap_analysis_path}")
    else:
        print("GAP-анализ не дал результатов.")

    print("--- Слой 3 завершен. ---\n")

    # --- Слой 4: Генерация Отчета ---
    print("--- Запуск Слой 4: ReportGenerator ---")
    try:
        report_generator = ReportGenerator(output_dir=output_dir)
        report_generator.generate_full_report()
        print("--- Слой 4 завершен. ---")
    except Exception as e:
        print(f"Произошла ошибка на этапе генерации отчета: {e}")


    print("\nПолный процесс анализа и генерации отчета завершен.")


if __name__ == "__main__":
    main()
