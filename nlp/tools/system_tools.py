from typing import Optional
from pydantic import Field
from nlp.tool_registry import ToolContract, ToolParameters

# --- Tool: Get Report ---

class GetReportParams(ToolParameters):
    """Parameters for the get_report tool."""
    project_name: str = Field(..., description="The name of the project to generate the report for.")
    date_range: Optional[str] = Field(None, description="The date range for the report, e.g., 'last_week', 'yesterday'.")

get_report_contract = ToolContract(
    name="get_report",
    description="Fetches and displays a report for a specific project.",
    parameters=GetReportParams
)


# --- Tool: Find Commits ---

class FindCommitsParams(ToolParameters):
    """Parameters for the find_commits tool."""
    project_name: str = Field(..., description="The name of the project to search for commits in.")
    author: Optional[str] = Field(None, description="Filter commits by a specific author.")
    message_contains: Optional[str] = Field(None, description="Filter commits by a string contained in the commit message.")

find_commits_contract = ToolContract(
    name="find_commits",
    description="Finds commits in a project, with optional filters for author and message content.",
    parameters=FindCommitsParams
)

# --- Tool: System Status ---

class SystemStatusParams(ToolParameters):
    """Parameters for the system_status tool. It takes no arguments."""
    pass

system_status_contract = ToolContract(
    name="get_system_status",
    description="Checks the current system status, such as CPU load, memory usage, and disk space.",
    parameters=SystemStatusParams
)
