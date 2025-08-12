# This file contains the main entry point for the Morpheus Protocol cycle.
import asyncio

from .analyzer import DreamAnalyzer, MockCodeScanner, MockOracleClient, MockNoosphereClient
from .architect import DreamArchitect
from .executor import REMExecutor, MockOrchestrator, MockGitClient, MockCenturion

async def run_morpheus_cycle():
    """
    This is the main function that orchestrates the entire Morpheus
    self-healing and optimization cycle.
    """
    print("\n" + "="*50)
    print("MORPHEUS MAIN CYCLE: INITIATED")
    print("="*50)

    # In a real app, these dependencies would be injected. Here we instantiate them.

    # PHASE 2: Run the Dream Analyzer.
    analyzer = DreamAnalyzer(MockCodeScanner(), MockOracleClient(), MockNoosphereClient())
    diagnostic_report = await analyzer.run_diagnostics()

    if not diagnostic_report.findings:
        print("MORPHEUS_MAIN: No findings from analyzer. Cycle complete. System is healthy.")
        print("="*50)
        print("MORPHEUS MAIN CYCLE: FINISHED")
        print("="*50 + "\n")
        return

    # PHASE 3: Run the Dream Architect.
    architect = DreamArchitect()
    tasks = architect.generate_tasks(diagnostic_report)
    prioritized_tasks = architect.prioritize_tasks(tasks)

    # PHASE 4: Run the REM Sleep execution loop.
    executor = REMExecutor(MockOrchestrator(), MockGitClient(), MockCenturion())
    await executor.execute_task_list(prioritized_tasks)

    print("\n" + "="*50)
    print("MORPHEUS MAIN CYCLE: FINISHED")
    print("="*50 + "\n")
