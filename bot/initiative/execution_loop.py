import json
import os
from bot import database

class AutonomousExecutionLoop:
    """
    Управляет жизненным циклом автономных инициатив:
    представляет их на утверждение и запускает одобренные.
    """
    def __init__(self, proposals_file="analysis_results/generated_initiatives.json", proposals=None):
        self.proposals_file = proposals_file
        self.proposals = proposals if proposals is not None else []

    def load_proposals(self):
        """Загружает сгенерированные предложения из локального файла, если они не были переданы напрямую."""
        if self.proposals:
            print("Предложения уже загружены напрямую.")
            return True

        print(f"Загрузка предложений из файла: {self.proposals_file}")
        try:
            with open(self.proposals_file, 'r', encoding='utf-8') as f:
                self.proposals = json.load(f)
            print(f"Загружено {len(self.proposals)} предложений.")
            return True
        except FileNotFoundError:
            print(f"Файл с предложениями не найден: {self.proposals_file}")
            return False

    def present_for_approval(self, proposal_index: int):
        """
        Представляет одно предложение на утверждение.
        В реальной системе это был бы интерактивный диалог.
        Здесь мы просто выводим информацию в консоль.
        """
        if not (0 <= proposal_index < len(self.proposals)):
            print("Неверный индекс предложения.")
            return

        proposal = self.proposals[proposal_index]
        contract = proposal.get('intent_contract', {})
        impact = proposal.get('impact_analysis', {})

        print("\n" + "="*50)
        print("=== ПРЕДЛОЖЕНИЕ НА УТВЕРЖДЕНИЕ ===")
        print("="*50)
        print(f"ИНИЦИАТИВА: {contract.get('title')} (ID: {contract.get('id')})")
        print(f"\n**Проблема:**\n{contract.get('problem_statement')}")
        print(f"\n**Предлагаемое решение:**\n{contract.get('proposed_solution', {}).get('goal')}")

        print("\n**АНАЛИЗ ПОСЛЕДСТВИЙ:**")
        print(f"- Оценка трудозатрат: {impact.get('estimated_effort')}")
        print(f"- Потенциальные риски: {', '.join(impact.get('risks', []))}")
        print(f"- Затрагиваемые модули: {', '.join(impact.get('affected_modules', []))}")

        print("\nТРЕБУЕТСЯ ВАШЕ ОДОБРЕНИЕ: [Да/Нет]")
        print("="*50)

    def approve_and_run(self, proposal_index: int):
        """
        Симулирует одобрение и запуск инициативы.
        """
        if not (0 <= proposal_index < len(self.proposals)):
            print("Неверный индекс предложения.")
            return

        print("\n--- ЗАПУСК ЦИКЛА ИСПОЛНЕНИЯ ---")

        # 1. Проверяем "красный телефон"
        is_safe_to_proceed = database.get_global_kill_switch_status()
        if not is_safe_to_proceed:
            print("!!! ВНИМАНИЕ: Глобальный 'красный телефон' активен. Автономное исполнение заблокировано.")
            # В реальной системе можно обновить статус на 'HALTED'
            return

        print("'Красный телефон' не активен. Продолжаем...")

        proposal = self.proposals[proposal_index]
        initiative_id = proposal.get('intent_contract', {}).get('id')
        title = proposal.get('intent_contract', {}).get('title')

        # 2. Обновляем статус в БД (симуляция, т.к. мы не сохраняли в БД)
        # В реальной системе мы бы читали из БД и обновляли бы там же.
        # database.update_initiative_status(initiative_id, 'APPROVED')
        # database.update_initiative_status(initiative_id, 'IN_PROGRESS')
        print(f"Статус инициативы '{title}' изменен на IN_PROGRESS (симуляция).")

        # 3. Передача в "Протокол Легион" (симуляция)
        print(f"Контракт '{title}' (ID: {initiative_id}) передан в 'Протокол Легион' для исполнения.")
        print("--- ЦИКЛ ИСПОЛНЕНИЯ ЗАВЕРШЕН (симуляция) ---")

        # 4. Финальное обновление статуса (симуляция)
        # database.update_initiative_status(initiative_id, 'COMPLETED')
        print(f"Статус инициативы '{title}' изменен на COMPLETED (симуляция).")
