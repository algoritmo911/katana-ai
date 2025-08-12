from pydantic import BaseModel, Field
from orchestrator.registry import register_capability
import time
import random

# --- Input and Output Schemas for the Capability ---

class CodeProfilerInput(BaseModel):
    module_path: str = Field(..., description="The path to the code module/file to be profiled.")
    line_limit: int = Field(10, description="The maximum number of slow lines to report.")

class ProfilerReportLine(BaseModel):
    line_number: int
    execution_time_ms: float
    line_content: str

class CodeProfilerOutput(BaseModel):
    report_url: str = Field(..., description="A URL pointing to the detailed profiling report.")
    slowest_lines: list[ProfilerReportLine] = Field(..., description="A list of the slowest lines of code found.")
    cyclomatic_complexity: float = Field(..., description="Calculated cyclomatic complexity for the module.")

# --- Capability Implementation ---

@register_capability(
    capability_name="run_code_profiler",
    description="Analyzes a Python module to find the slowest lines of code and calculates its cyclomatic complexity.",
    input_schema=CodeProfilerInput,
    output_schema=CodeProfilerOutput
)
def profile_code(input: CodeProfilerInput) -> CodeProfilerOutput:
    """
    Simulates profiling a code module.

    In a real implementation, this would involve using a library like cProfile
    to analyze the code. For this example, we'll just generate dummy data.
    """
    print(f"INFO: Profiling module '{input.module_path}'...")

    # --- Start of failure simulation for self-correction ---
    if "fail" in input.module_path:
        print("INFO: Simulating a tool failure for self-correction test.")
        raise ValueError("Module is too large to profile. Profiling failed.")
    # --- End of failure simulation ---

    time.sleep(2) # Simulate work

    # Generate fake line reports
    slow_lines = []
    for i in range(min(input.line_limit, 5)): # Generate up to 5 fake slow lines
        slow_lines.append(
            ProfilerReportLine(
                line_number=random.randint(10, 100),
                execution_time_ms=random.uniform(50.0, 500.0),
                line_content=f"result = old_function(arg{i}) * {random.randint(2,10)}"
            )
        )

    # Generate a fake report URL
    report_id = random.randint(1000, 9999)
    report_url = f"https://profiler.example.com/reports/{report_id}"

    # Calculate fake complexity
    complexity = random.uniform(1.0, 25.0)

    print(f"INFO: Profiling complete. Report at {report_url}")

    return CodeProfilerOutput(
        report_url=report_url,
        slowest_lines=slow_lines,
        cyclomatic_complexity=complexity
    )
