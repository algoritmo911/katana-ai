# =======================================================================================================================
# ID ПРОТОКОЛА: Telos-v1.0-TheSeagullNebula
# КОМПОНЕНТ: Katana Master Control Program (MCP)
# ОПИСАНИЕ: Главный управляющий цикл агента. Запускает мета-когнитивный цикл "Телос"
# для генерации целей, а затем передает их тактическому циклу OODA-P для выполнения.
# =======================================================================================================================

from core.world_modeler import WorldModeler
from core.neurovault import Neurovault
from core.diagnost import Diagnost
from core.cassandra import Cassandra
from core.dream_engine import DreamEngine
from core.action_space import ActionSpace
from core.simulation_matrix import SimulationMatrix
from core.value_judgement_engine import ValueJudgementEngine
from core.goal_generator import GoalGenerator
from agent_loop import KatanaAgent

def main():
    """
    The main entry point for the fully autonomous Katana agent.
    """
    print("="*60)
    print("KATANA MASTER CONTROL PROGRAM INITIALIZING...")
    print("="*60)

    # --- Phase 1: Initialize all components ---
    # The components for the Telos Meta-Cognitive Loop
    world_modeler = WorldModeler(Neurovault(), Diagnost(), Cassandra())
    dream_engine = DreamEngine(ActionSpace(), SimulationMatrix())
    vje = ValueJudgementEngine()
    goal_generator = GoalGenerator()

    # The agent that runs the OODA-P Tactical Loop
    katana_agent = KatanaAgent()

    print("\nAll components initialized. Starting main loop.\n")

    # --- This would be a continuous loop in a real deployment ---
    # while True:

    # --- Phase 2: Run one full Telos Meta-Cognitive Cycle ---
    print("="*20 + " TELOS META-COGNITIVE CYCLE START " + "="*19)

    # 1. Perceive the world
    initial_state = world_modeler.create_world_state_snapshot()
    print("\n[TELOS] Step 1: World state snapshot created.")

    # 2. Dream of the future
    nebula = dream_engine.generate_future_nebula(initial_state, depth=3, breadth=2)
    print(f"[TELOS] Step 2: Dreamt of the future, creating a nebula with {len(nebula)} nodes.")

    # 3. Judge the dreams
    landscape = vje.evaluate_nebula(nebula, initial_state)
    print("[TELOS] Step 3: Evaluated dreams, creating a landscape of desires.")

    # 4. Form a desire (goal)
    meta_goal = goal_generator.generate_goal(landscape)
    print(f"[TELOS] Step 4: A desire has been born. Goal: {meta_goal}")

    print("="*21 + " TELOS META-COGNITIVE CYCLE END " + "="*20)

    # --- Phase 3: Submit the self-generated goal to the Tactical Loop ---
    if meta_goal:
        print("\n[MCP] Submitting self-generated goal to the tactical layer...")
        katana_agent.goal_prioritizer.add_meta_goal(meta_goal)
    else:
        print("\n[MCP] No goal was generated in this cycle. Agent will react to environment only.")

    # --- Phase 4: Run one OODA-P Tactical Cycle ---
    # The tactical loop will now prioritize the meta-goal alongside any environmental goals.
    katana_agent.run_single_cycle()

    print("\n" + "="*60)
    print("KATANA MASTER CONTROL PROGRAM CYCLE COMPLETE.")
    print("="*60)
    # time.sleep(3600) # In a real deployment, wait before starting the next meta-cycle

if __name__ == '__main__':
    main()
