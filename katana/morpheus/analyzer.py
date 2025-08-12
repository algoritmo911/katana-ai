import asyncio
import uuid
from datetime import datetime
from typing import List

from .contracts import (
    DiagnosticReport,
    CodeDebtFinding,
    PerformanceRegressionFinding,
    KnowledgeIntegrityFinding
)

# --- Mock Clients for Dependencies ---
# In a real application, these would be proper clients for other services.

class MockCodeScanner:
    async def find_technical_debt(self) -> List[CodeDebtFinding]:
        print("DREAM_ANALYZER: Auditing code health...")
        await asyncio.sleep(1) # Simulate I/O
        return [
            CodeDebtFinding(
                file_path="katana/morpheus/monitor.py",
                line_number=45,
                cyclomatic_complexity=22,
                details="Function `is_idle` has high complexity."
            )
        ]

class MockOracleClient:
    async def find_performance_regressions(self) -> List[PerformanceRegressionFinding]:
        print("DREAM_ANALYZER: Auditing performance metrics...")
        await asyncio.sleep(1.5) # Simulate I/O
        return [
            PerformanceRegressionFinding(
                endpoint_or_function="/api/v1/orchestrator/plan",
                latency_increase_ms=630.5,
                baseline_ms=450.0,
                current_ms=1080.5
            )
        ]

class MockNoosphereClient:
    async def find_integrity_issues(self) -> List[KnowledgeIntegrityFinding]:
        print("DREAM_ANALYZER: Auditing knowledge graph integrity...")
        await asyncio.sleep(0.5) # Simulate I/O
        return [
            KnowledgeIntegrityFinding(
                issue_type="orphan_concept",
                concept_id="uuid-morpheus-cycle-123",
                details="Concept is not linked to any other part of the graph."
            )
        ]

# --- Main Analyzer Class ---

class DreamAnalyzer:
    def __init__(self, code_scanner, oracle_client, noosphere_client):
        self.code_scanner = code_scanner
        self.oracle_client = oracle_client
        self.noosphere_client = noosphere_client

    async def run_diagnostics(self) -> DiagnosticReport:
        """
        Runs the full diagnostic pipeline by executing all audits in parallel.
        """
        print("DREAM_ANALYZER: Beginning full diagnostic scan.")

        # Schedule all audit tasks to run concurrently
        code_findings_task = self.audit_code()
        perf_findings_task = self.audit_performance()
        knowledge_findings_task = self.audit_knowledge()

        # Wait for all audits to complete
        results = await asyncio.gather(
            code_findings_task,
            perf_findings_task,
            knowledge_findings_task,
            return_exceptions=True # Prevent one failure from stopping all diagnostics
        )

        # Flatten the list of findings, filtering out any exceptions
        all_findings = []
        for res in results:
            if isinstance(res, Exception):
                print(f"ERROR: A diagnostic audit failed: {res}")
            else:
                all_findings.extend(res)

        report = DiagnosticReport(
            report_id=f"diag-{uuid.uuid4()}",
            timestamp_utc=datetime.utcnow().isoformat(),
            findings=all_findings
        )

        print(f"DREAM_ANALYZER: Diagnostics complete. Found {len(all_findings)} issues.")
        return report

    async def audit_code(self) -> List[CodeDebtFinding]:
        return await self.code_scanner.find_technical_debt()

    async def audit_performance(self) -> List[PerformanceRegressionFinding]:
        return await self.oracle_client.find_performance_regressions()

    async def audit_knowledge(self) -> List[KnowledgeIntegrityFinding]:
        return await self.noosphere_client.find_integrity_issues()

async def run_analyzer_simulation():
    """A helper function to simulate the analyzer for testing."""
    print("\n--- Running Dream Analyzer Simulation ---")

    # Instantiate mock clients
    scanner = MockCodeScanner()
    oracle = MockOracleClient()
    noosphere = MockNoosphereClient()

    # Instantiate and run the analyzer
    analyzer = DreamAnalyzer(scanner, oracle, noosphere)
    report = await analyzer.run_diagnostics()

    print("\n--- Generated Diagnostic Report ---")
    # Pydantic v2 uses model_dump_json
    print(report.model_dump_json(indent=2))
    print("\n--- Simulation Complete ---")

if __name__ == "__main__":
    asyncio.run(run_analyzer_simulation())
