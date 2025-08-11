import os
import re
import json
from bot.nlp_clients.openai_client import OpenAIClient

class FailureAnalyzer:
    """
    Analyzes logs to find the root cause of a failure.
    """

    def __init__(self, log_file_path: str = None):
        """
        Initializes the FailureAnalyzer.

        Args:
            log_file_path: The path to the log file. If not provided, it will be
                           read from the LOG_FILE_PATH environment variable.
        """
        self.log_file_path = log_file_path or os.environ.get("LOG_FILE_PATH")
        if not self.log_file_path:
            raise ValueError("Log file path not provided or found in environment variables.")
        self.nlp_client = OpenAIClient()

    def analyze(self, trace_id: str) -> dict:
        """
        Analyzes the log file for a given trace_id to determine the root cause of a failure.

        Args:
            trace_id: The trace ID of the failed operation.

        Returns:
            A dictionary containing the analysis, including the file, line number,
            and a root cause hypothesis.
        """
        if not os.path.exists(self.log_file_path):
            return {"error": "Log file not found."}

        log_context = []
        with open(self.log_file_path, "r") as f:
            for line in f:
                if trace_id in line:
                    log_context.append(line)

        if not log_context:
            return {"error": f"No logs found for trace_id: {trace_id}"}

        # Find the traceback and the error message
        traceback_lines = []
        in_traceback = False
        for line in log_context:
            if "Traceback (most recent call last):" in line:
                in_traceback = True
            if in_traceback:
                traceback_lines.append(line)

        if not traceback_lines:
            return {"error": "No traceback found in the logs for this trace_id."}

        traceback_str = "".join(traceback_lines)

        # Extract file and line number from traceback
        file_path, line_num = FailureAnalyzer._extract_file_and_line(traceback_str)
        if not file_path:
            return {"error": f"Could not extract file and line from traceback: {traceback_str}"}

        # Formulate a prompt for the LLM
        prompt = self._create_llm_prompt(log_context, traceback_str)

        # Get the root cause hypothesis from the LLM
        try:
            hypothesis = self.nlp_client.generate_text(prompt)
        except Exception as e:
            return {"error": f"Failed to get root cause hypothesis from LLM: {e}"}

        return {
            "file": file_path,
            "line": line_num,
            "root_cause_hypothesis": hypothesis,
        }

    @staticmethod
    def _extract_file_and_line(traceback_str: str) -> (str, int):
        """
        Extracts the file path and line number from a traceback string.
        This is a simple implementation and might need to be made more robust.
        """
        match = re.search(r'File "(.+)", line (\d+), in .*\n', traceback_str)
        if match:
            return match.group(1), int(match.group(2))
        return None, None

    def _create_llm_prompt(self, log_context: list, traceback_str: str) -> str:
        """
        Creates a prompt for the LLM to analyze the failure.
        """
        prompt = (
            "Analyze the following logs and traceback to determine the root cause of the failure.\n"
            "Provide a concise, one-sentence hypothesis for the root cause.\n\n"
            "--- LOG CONTEXT ---\n"
            f"{''.join(log_context)}\n\n"
            "--- TRACEBACK ---\n"
            f"{traceback_str}\n\n"
            "--- ROOT CAUSE HYPOTHESIS ---\n"
        )
        return prompt
