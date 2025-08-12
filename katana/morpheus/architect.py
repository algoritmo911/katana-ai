import yaml
from typing import List, Dict

from .contracts import DiagnosticReport, CodeDebtFinding, PerformanceRegressionFinding, KnowledgeIntegrityFinding

# This would be a more sophisticated Pydantic model in a real system.
IntentContract = Dict

class DreamArchitect:
    """
    Translates a diagnostic report into a prioritized list of actionable tasks (IntentContracts).
    """
    def __init__(self):
        # Load the prioritization config from the TDD (or a real config file)
        # For simplicity, we'll hardcode the weights here based on the TDD.
        self.priority_weights = {
            "code_debt": {"impact": 5, "urgency": 3},
            "performance_regression": {"impact": 8, "urgency": 7},
            "knowledge_integrity": {"impact": 4, "urgency": 6},
            "conceptual_hotspot": {"impact": 3, "urgency": 4},
        }

    def generate_tasks(self, report: DiagnosticReport) -> List[IntentContract]:
        """
        Converts each finding in a diagnostic report into a formal IntentContract.
        """
        print(f"DREAM_ARCHITECT: Generating tasks from {len(report.findings)} findings.")
        tasks = []
        for finding in report.findings:
            # This is where the "Prometheus Protocol" (LLM call) would happen.
            # We will mock this by using simple f-string templates.
            goal = self._create_goal_from_finding(finding)

            task = {
                "goal": goal,
                "constraints": ["Must pass all existing unit tests."],
                "source": "morpheus-protocol",
                "raw_finding": finding.model_dump()
            }
            tasks.append(task)

        print(f"DREAM_ARCHITECT: Generated {len(tasks)} tasks.")
        return tasks

    def _create_goal_from_finding(self, finding) -> str:
        """Mocks the LLM call to formulate a human-readable goal."""
        if isinstance(finding, CodeDebtFinding):
            return f"Refactor the function at {finding.file_path} (line ~{finding.line_number}) to reduce its cyclomatic complexity below 20."
        if isinstance(finding, PerformanceRegressionFinding):
            return f"Investigate and fix the performance regression for {finding.endpoint_or_function}, which has slowed by {finding.latency_increase_ms:.0f}ms."
        if isinstance(finding, KnowledgeIntegrityFinding):
            return f"Resolve the knowledge graph integrity issue: '{finding.issue_type}' for concept {finding.concept_id}."
        # Add other finding types here
        return "Address an unspecified system issue."

    def prioritize_tasks(self, tasks: List[IntentContract]) -> List[IntentContract]:
        """
        Sorts a list of tasks based on a weighted priority score.
        """
        print(f"DREAM_ARCHITECT: Prioritizing {len(tasks)} tasks.")

        def calculate_score(task: IntentContract) -> float:
            finding_type = task['raw_finding']['type']
            weights = self.priority_weights.get(finding_type, {"impact": 1, "urgency": 1})

            # Severity is not explicitly modeled here for simplicity, we use a fixed value.
            # The TDD suggests this would be proportional to the finding's data.
            severity = 5

            score = (weights['impact'] * weights['urgency']) + (severity * 0.5)
            # Add a small value from the finding to make scores unique for sorting
            if finding_type == 'performance_regression':
                score += task['raw_finding']['latency_increase_ms'] / 1000.0
            elif finding_type == 'code_debt':
                score += task['raw_finding']['cyclomatic_complexity'] / 100.0

            return score

        sorted_tasks = sorted(tasks, key=calculate_score, reverse=True)

        print("DREAM_ARCHITECT: Task prioritization complete.")
        return sorted_tasks

async def run_architect_simulation():
    """A helper function to simulate the architect for testing."""
    from .analyzer import DreamAnalyzer, MockCodeScanner, MockOracleClient, MockNoosphereClient

    print("\n--- Running Dream Architect Simulation ---")

    # 1. First, get a diagnostic report from the analyzer
    print("\nStep 1: Running Analyzer to get a report...")
    analyzer = DreamAnalyzer(MockCodeScanner(), MockOracleClient(), MockNoosphereClient())
    report = await analyzer.run_diagnostics()

    # 2. Now, process the report with the architect
    print("\nStep 2: Running Architect to process the report...")
    architect = DreamArchitect()
    tasks = architect.generate_tasks(report)
    prioritized_tasks = architect.prioritize_tasks(tasks)

    print("\n--- Generated Prioritized Task List ---")
    import json
    print(json.dumps(prioritized_tasks, indent=2))
    print("\n--- Simulation Complete ---")


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_architect_simulation())
