import os
from bot.initiative.execution_loop import AutonomousExecutionLoop

from dotenv import load_dotenv

def main():
    """
    Демонстрирует цикл утверждения и запуска для одной инициативы.
    """
    # Загружаем переменные окружения
    load_dotenv()

    print("--- Запуск демонстрации цикла утверждения ---")

    execution_loop = AutonomousExecutionLoop()

    # 1. Загружаем все сгенерированные предложения
    if not execution_loop.load_proposals():
        return # Выход, если нет предложений для обработки

    # 2. Представляем первое предложение на утверждение
    print("\nСИМУЛЯЦИЯ: Представление первого предложения на утверждение Оператору...")
    execution_loop.present_for_approval(0)

    # 3. Симулируем одобрение и запуск этого предложения
    print("\nСИМУЛЯЦИЯ: Оператор одобрил предложение. Запускаем исполнение...")
    execution_loop.approve_and_run(0)

    print("\n--- Демонстрация цикла утверждения завершена ---")

if __name__ == "__main__":
    main()
