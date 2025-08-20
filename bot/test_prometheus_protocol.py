import pytest
import os
import json
from unittest.mock import patch, MagicMock

from dotenv import load_dotenv

# Загружаем переменные окружения до импорта модулей бота
load_dotenv()

from bot.initiative.hypothesis_generator import HypothesisGenerator
from bot.simulation.impact_simulator import ImpactSimulator
from bot.initiative.execution_loop import AutonomousExecutionLoop
from bot.initiative.models import InitiativeProposal

# Пропускаем тесты, если не заданы ключи API, чтобы не падать в CI/CD
requires_api_keys = pytest.mark.skipif(
    not (os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY") and os.getenv("OPENAI_API_KEY")),
    reason="Тест требует наличия реальных ключей API в окружении"
)

@requires_api_keys
@pytest.mark.integration
class TestPrometheusProtocol:

    @patch('bot.database.get_global_kill_switch_status')
    def test_full_initiative_cycle(self, mock_get_kill_switch):
        """
        Тестирует полный цикл Протокола "Прометей":
        1. Генерация гипотезы (IntentContract) из проблемы.
        2. Симуляция последствий (ImpactAnalysis).
        3. Запуск "одобренной" инициативы.
        """
        # --- 1. Настройка ---
        mock_get_kill_switch.return_value = True # Симулируем, что "красный телефон" выключен
        problem_statement = "Процесс код-ревью замедляется из-за отсутствия временных тестовых окружений для каждого PR."

        hypothesis_generator = HypothesisGenerator()
        impact_simulator = ImpactSimulator()

        # --- 2. Генерация и Симуляция ---
        print("\n--- Шаг 1: Генерация контракта ---")
        contract = hypothesis_generator.generate_contract(problem_statement)
        assert contract is not None, "HypothesisGenerator не смог создать контракт"
        assert isinstance(contract.id, str)
        # Проверяем, что заголовок не пустой, а не его точное содержимое
        assert contract.title and isinstance(contract.title, str)

        print("\n--- Шаг 2: Симуляция последствий ---")
        impact = impact_simulator.simulate_impact(contract)
        assert impact is not None, "ImpactSimulator не смог провести анализ"
        assert len(impact.risks) > 0
        assert impact.estimated_effort in ['Малый', 'Средний', 'Большой']

        # --- 3. Исполнение ---
        print("\n--- Шаг 3: Запуск цикла исполнения ---")
        # Создаем предложение и передаем его в цикл напрямую для теста
        proposal = InitiativeProposal(
            status="APPROVED", # Симулируем, что оно уже одобрено
            intent_contract=contract,
            impact_analysis=impact
        )

        # Модифицируем AEL, чтобы он принимал предложение напрямую
        execution_loop = AutonomousExecutionLoop(proposals_file=None) # Не будем читать из файла
        execution_loop.proposals = [proposal.model_dump(mode='json')] # Устанавливаем предложение

        # Запускаем цикл для этого конкретного предложения
        execution_loop.approve_and_run(0)

        # Проверяем, что функция проверки "красного телефона" была вызвана
        mock_get_kill_switch.assert_called_once()

        print("\n--- Тест полного цикла 'Прометей' успешно завершен ---")
