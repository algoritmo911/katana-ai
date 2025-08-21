import pytest
from unittest.mock import patch, MagicMock
import os

from katana.chrysalis.afe.log_analyzer import LogAnalyzer
from katana.chrysalis.afe.engine import AnomalyForensicsEngine
from katana.chrysalis.models import CausalGraph

@pytest.fixture
def mock_log_file(tmp_path):
    """Creates a temporary log file with a sample traceback."""
    log_content = """
    INFO: Service started
    DEBUG: Request received for trace_id: 12345
    INFO: Processing request for trace_id: 12345
    ERROR: An error occurred for trace_id: 12345
    Traceback (most recent call last):
      File "/app/katana/main.py", line 50, in handle_request
        process_data(data)
      File "/app/katana/worker.py", line 100, in process_data
        result = external_api.call()
    TypeError: 'NoneType' object is not callable
    INFO: Request finished for trace_id: 12345
    """
    log_file = tmp_path / "test.log"
    log_file.write_text(log_content)
    return str(log_file)

class TestLogAnalyzer:
    def test_analyze_trace_success(self, mock_log_file):
        """Tests that the LogAnalyzer successfully parses a log file."""
        analyzer = LogAnalyzer(log_file_path=mock_log_file)
        result = analyzer.analyze_trace("12345")

        assert result["success"] is True
        assert "Traceback (most recent call last):" in result["traceback"]
        assert "TypeError: 'NoneType' object is not callable" in result["traceback"]
        assert result["file_path"] == "/app/katana/worker.py"
        assert result["line_number"] == 100

    def test_analyze_trace_no_trace_id(self, mock_log_file):
        """Tests the case where the trace_id is not in the log file."""
        analyzer = LogAnalyzer(log_file_path=mock_log_file)
        result = analyzer.analyze_trace("non_existent_id")
        assert "error" in result
        assert result["error"] == "No logs found for trace_id: non_existent_id"

    def test_log_file_not_found(self):
        """Tests the case where the log file does not exist."""
        analyzer = LogAnalyzer(log_file_path="/non/existent/path.log")
        result = analyzer.analyze_trace("12345")
        assert "error" in result
        assert result["error"] == "Log file not found at /non/existent/path.log."


class TestAnomalyForensicsEngine:
    @patch('katana.chrysalis.afe.engine.LogAnalyzer')
    def test_analyze_anomaly_builds_graph(self, MockLogAnalyzer):
        """
        Tests that the AFE engine correctly orchestrates the analysis and
        builds a CausalGraph.
        """
        # Arrange
        mock_analysis_result = {
            "success": True,
            "log_context": ["line1", "line2"],
            "traceback": "Traceback...",
            "file_path": "/app/katana/worker.py",
            "line_number": 100,
        }
        mock_log_analyzer_instance = MockLogAnalyzer.return_value
        mock_log_analyzer_instance.analyze_trace.return_value = mock_analysis_result

        engine = AnomalyForensicsEngine(log_file_path="dummy/path.log")

        # Act
        graph = engine.analyze_anomaly("12345", "Test Anomaly")

        # Assert
        assert isinstance(graph, CausalGraph)
        assert len(graph.nodes) == 2  # Anomaly hypothesis + traceback
        assert len(graph.edges) == 1  # Link between them

        # Check the traceback node
        tb_node = graph.get_node(graph.edges[0].source_id)
        assert tb_node.event_type == "traceback"
        assert tb_node.data["file_path"] == "/app/katana/worker.py"

        # Check that the LogAnalyzer was called correctly
        mock_log_analyzer_instance.analyze_trace.assert_called_once_with("12345")

    @patch('katana.chrysalis.afe.engine.LogAnalyzer')
    def test_analyze_anomaly_handles_log_analysis_failure(self, MockLogAnalyzer):
        """
        Tests that the AFE engine handles cases where log analysis fails.
        """
        # Arrange
        mock_analysis_result = {"error": "Something went wrong"}
        mock_log_analyzer_instance = MockLogAnalyzer.return_value
        mock_log_analyzer_instance.analyze_trace.return_value = mock_analysis_result

        engine = AnomalyForensicsEngine(log_file_path="dummy/path.log")

        # Act
        graph = engine.analyze_anomaly("12345", "Test Anomaly")

        # Assert
        assert isinstance(graph, CausalGraph)
        assert len(graph.nodes) == 1  # Only the initial anomaly hypothesis node
        assert len(graph.edges) == 0
        mock_log_analyzer_instance.analyze_trace.assert_called_once_with("12345")
