import os
from .failure_analyzer import FailureAnalyzer
from .code_patcher import CodePatcher
from .patch_validator import PatchValidator
from .git_integration import create_pull_request

class SelfHealOrchestrator:
    """
    Orchestrates the entire self-healing process.
    """

    def __init__(self):
        self.failure_analyzer = FailureAnalyzer()
        self.code_patcher = CodePatcher()
        self.patch_validator = PatchValidator()

    def run(self, trace_id: str):
        """
        Runs the full self-healing cycle for a given trace_id.

        Args:
            trace_id: The trace ID of the failed operation.
        """
        print(f"Starting self-healing process for trace_id: {trace_id}")

        # 1. Analyze the failure
        analysis = self.failure_analyzer.analyze(trace_id)
        if "error" in analysis:
            print(f"Failed to analyze failure: {analysis['error']}")
            return
        print(f"Analysis complete. Hypothesis: {analysis['root_cause_hypothesis']}")

        # 2. Generate a patch
        patch_data = self.code_patcher.generate_patch(analysis)
        if "error" in patch_data:
            print(f"Failed to generate patch: {patch_data['error']}")
            return
        print("Patch generated successfully.")

        # 3. Validate the patch
        file_path = analysis["file"]
        original_snippet = patch_data["original_snippet"]
        patched_snippet = patch_data["patched_snippet"]

        is_valid = self.patch_validator.validate_patch(file_path, original_snippet, patched_snippet)
        if not is_valid:
            print("Patch validation failed. Aborting.")
            return
        print("Patch validated successfully.")

        # 4. Create a pull request
        pr_title = f"Fix: Self-healing patch for {os.path.basename(file_path)}"
        pr_body = self._create_pr_body(analysis, original_snippet, patched_snippet)

        # The head branch should be unique for each fix
        head_branch = f"self-heal/{os.path.basename(file_path)}-{trace_id[:8]}"

        print(f"Creating pull request on branch: {head_branch}")
        # In a real scenario, we would need to commit the change and push the branch first.
        # This is a simplified version for demonstration.
        # For now, we will just print the PR details.

        # pr, message = create_pull_request(pr_title, pr_body, head_branch)
        # if pr:
        #     print(f"Pull request created successfully: {pr['html_url']}")
        # else:
        #     print(f"Failed to create pull request: {message}")
        print("\n--- PULL REQUEST DETAILS ---")
        print(f"Title: {pr_title}")
        print(f"Branch: {head_branch}")
        print(f"Body:\n{pr_body}")
        print("--------------------------\n")
        print("Self-healing process complete.")

    def _create_pr_body(self, analysis: dict, original_snippet: str, patched_snippet: str) -> str:
        """
        Creates a formatted body for the pull request.
        """
        body = (
            "## Katana Self-Healing Report\n\n"
            f"**File:** `{analysis['file']}`\n"
            f"**Line:** `{analysis['line']}`\n\n"
            "### Root Cause Hypothesis\n"
            f"{analysis['root_cause_hypothesis']}\n\n"
            "### Proposed Patch\n"
            "The following patch has been automatically generated and validated against the test suite.\n\n"
            "#### Original Code\n"
            "```python\n"
            f"{original_snippet}\n"
            "```\n\n"
            "#### Patched Code\n"
            "```python\n"
            f"{patched_snippet}\n"
            "```\n"
        )
        return body
