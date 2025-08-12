from pydantic import BaseModel, Field
from orchestrator.registry import register_capability
import random

# --- Input and Output Schemas ---

class StaticAnalyzerInput(BaseModel):
    module_path: str = Field(..., description="The path to the code module/file to be analyzed.")

class StaticAnalysisFinding(BaseModel):
    line_number: int
    severity: str
    message: str

class StaticAnalyzerOutput(BaseModel):
    cyclomatic_complexity: float = Field(..., description="Calculated cyclomatic complexity for the module.")
    findings: list[StaticAnalysisFinding] = Field(..., description="A list of potential issues found in the code.")

# --- Capability Implementation ---

@register_capability(
    capability_name="run_static_analyzer",
    description="A lightweight tool that runs static analysis on a Python module to calculate cyclomatic complexity and find potential code issues. Use this as an alternative if a full profiler fails or is too slow.",
    input_schema=StaticAnalyzerInput,
    output_schema=StaticAnalyzerOutput
)
def analyze_code_statically(input: StaticAnalyzerInput) -> StaticAnalyzerOutput:
    """
    Simulates running static analysis on a code module.
    """
    print(f"INFO: Running lightweight static analysis on module '{input.module_path}'...")

    # Simulate findings
    findings = [
        StaticAnalysisFinding(
            line_number=random.randint(10, 100),
            severity="Warning",
            message="Function has high cyclomatic complexity."
        ),
        StaticAnalysisFinding(
            line_number=random.randint(10, 100),
            severity="Info",
            message="Variable name is too short."
        )
    ]

    complexity = random.uniform(1.0, 25.0)

    print(f"INFO: Static analysis complete.")

    return StaticAnalyzerOutput(
        cyclomatic_complexity=complexity,
        findings=findings
    )
