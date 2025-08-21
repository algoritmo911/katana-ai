import os
import re
from typing import Dict, Any, Optional, Tuple, List

class LogAnalyzer:
    """
    Analyzes log files to extract structured information about failures.
    """

    def __init__(self, log_file_path: str = None):
        """
        Initializes the LogAnalyzer.

        Args:
            log_file_path: The path to the log file. If not provided, it will be
                           read from the LOG_FILE_PATH environment variable.
        """
        self.log_file_path = log_file_path or os.environ.get("LOG_FILE_PATH")
        if not self.log_file_path:
            # In a real scenario, we might have different ways to get logs,
            # but for now, we depend on this file.
            raise ValueError("Log file path not provided or found in environment variables.")

    def analyze_trace(self, trace_id: str) -> Dict[str, Any]:
        """
        Analyzes the log file for a given trace_id to extract failure details.

        Args:
            trace_id: The trace ID of the failed operation.

        Returns:
            A dictionary containing the analysis, including log context, traceback,
            and extracted file and line number.
        """
        if not os.path.exists(self.log_file_path):
            return {"error": f"Log file not found at {self.log_file_path}."}

        try:
            with open(self.log_file_path, "r") as f:
                all_lines = f.readlines()

            # Find all lines related to the trace_id to provide context
            log_context = [line for line in all_lines if trace_id in line]
            if not log_context:
                return {"error": f"No logs found for trace_id: {trace_id}"}

            # Search for the traceback in the full log content, not just the
            # filtered context, as traceback lines may not contain the trace_id.
            traceback_str = self._extract_traceback(all_lines)
            if not traceback_str:
                return {
                    "error": "No traceback found in the log file.",
                    "log_context": log_context,
                }

            file_path, line_num = self._extract_file_and_line(traceback_str)

            return {
                "success": True,
                "log_context": log_context,
                "traceback": traceback_str,
                "file_path": file_path,
                "line_number": line_num,
            }

        except Exception as e:
            return {"error": f"An unexpected error occurred during log analysis: {e}"}

    def _get_log_context(self, trace_id: str) -> List[str]:
        """Reads the log file and returns all lines containing the trace_id."""
        log_context = []
        with open(self.log_file_path, "r") as f:
            for line in f:
                if trace_id in line:
                    log_context.append(line)
        return log_context

    @staticmethod
    def _extract_traceback(log_context: List[str]) -> Optional[str]:
        """Extracts the full traceback from a list of log lines."""
        traceback_lines = []
        in_traceback = False
        for line in log_context:
            if "Traceback (most recent call last):" in line:
                in_traceback = True
            if in_traceback:
                traceback_lines.append(line)

        return "".join(traceback_lines) if traceback_lines else None

    @staticmethod
    def _extract_file_and_line(traceback_str: str) -> Tuple[Optional[str], Optional[int]]:
        """
        Extracts the most relevant file path and line number from a traceback string.
        It looks for the last file in the traceback that is part of the application's
        source code, avoiding library files if possible.
        """
        # This regex is a bit more specific to find file paths in typical Python tracebacks.
        # It captures the file path and the line number.
        matches = re.findall(r'File "(.+?)", line (\d+), in .+', traceback_str)

        if not matches:
            return None, None

        # Often, the last entry in the traceback is the most relevant one from the app code.
        # This is a heuristic and might need to be improved. For now, we take the last one.
        last_match = matches[-1]
        file_path = last_match[0]
        line_num = int(last_match[1])

        return file_path, line_num
