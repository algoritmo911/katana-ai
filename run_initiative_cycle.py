import os
import json
from bot.initiative.hypothesis_generator import HypothesisGenerator
from bot.simulation.impact_simulator import ImpactSimulator
from bot.initiative.models import InitiativeProposal
from bot import database

def main():
    """
    Запускает полный цикл генерации и симуляции инициатив на основе
    результатов стратегического анализа.
    """
    # Вручную устанавливаем переменные окружения
    os.environ["OPENAI_API_KEY"] = "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"
    os.environ["SUPABASE_KEY"] = "sb_secret_wtRSbhoCKkW53FAn2UzFpg_ED78K1LU"
    os.environ["SUPABASE_URL"] = "https://pmcaojgdrszvujvwzxrc.supabase.co"

    analysis_file = "analysis_results/gap_analysis.json"
    print(f"Загрузка файла с GAP-анализом: {analysis_file}")

    try:
        with open(analysis_file, 'r', encoding='utf-8') as f:
            gap_data = json.load(f)
    except FileNotFoundError:
        print(f"Ошибка: Файл {analysis_file} не найден. Запустите сначала 'run_analysis.py'.")
        return

    # Инициализируем генераторы
    hypothesis_generator = HypothesisGenerator()
    impact_simulator = ImpactSimulator()

    # Собираем все проблемы в один список
    all_proposals = []
    problems = []
    problems.extend(gap_data.get('gaps', []))
    problems.extend(gap_data.get('white_spots', []))
    problems.extend(gap_data.get('contradictions', []))

    print(f"Найдено {len(problems)} проблем/возможностей для проработки.")

    for i, problem in enumerate(problems):
        print(f"\n--- Обработка проблемы {i+1}/{len(problems)} ---")

        # 1. Генерируем контракт
        contract = hypothesis_generator.generate_contract(problem)
        if not contract:
            print("Не удалось сгенерировать контракт. Переход к следующей проблеме.")
            continue

        # 2. Симулируем последствия
        impact = impact_simulator.simulate_impact(contract)
        if not impact:
            print("Не удалось симулировать последствия. Переход к следующей проблеме.")
            continue

        # 3. Собираем полное предложение
        proposal = InitiativeProposal(
            status="PENDING_APPROVAL",
            intent_contract=contract,
            impact_analysis=impact
        )

        # 4. Сохраняем предложение в базу данных
        # ВРЕМЕННЫЙ КОСТЫЛЬ: Сохраняем результат в локальный файл вместо БД
        all_proposals.append(proposal.model_dump(mode='json'))
        print(f"Предложение '{contract.title}' подготовлено для локального сохранения.")

    # Сохраняем все предложения в один файл
    proposals_path = "analysis_results/generated_initiatives.json"
    with open(proposals_path, 'w', encoding='utf-8') as f:
        json.dump(all_proposals, f, ensure_ascii=False, indent=2)

    print(f"\nВсе сгенерированные предложения сохранены в файл: {proposals_path}")
    print("Цикл генерации и симуляции инициатив завершен (с локальным сохранением).")

if __name__ == "__main__":
    main()
