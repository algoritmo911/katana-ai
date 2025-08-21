import hashlib
import uuid
from datetime import datetime

from .log_analyzer import LogAnalyzer
from ..models import CausalGraph, EventNode, CausalEdge

class AnomalyForensicsEngine:
    """
    Orchestrates the anomaly forensics process by running various collectors
    and analyzers to build a causal graph of a failure.
    """

    def __init__(self, log_file_path: str = None):
        """
        Initializes the AFE.

        Args:
            log_file_path: Path to the log file, to be passed to collectors.
        """
        # In a more complex setup, we would have a registry of collectors.
        self.log_analyzer = LogAnalyzer(log_file_path=log_file_path)
        # self.git_collector = GitCollector() # To be added in the future
        # self.metrics_collector = MetricsCollector() # To be added in the future

    def analyze_anomaly(self, trace_id: str, anomaly_description: str) -> CausalGraph:
        """
        Performs a full forensic analysis for a given anomaly.

        Args:
            trace_id: The unique trace ID associated with the anomaly.
            anomaly_description: A human-readable description of the anomaly.

        Returns:
            A CausalGraph object representing the analysis.
        """
        anomaly_id = str(uuid.uuid4())
        graph = CausalGraph(anomaly_id=anomaly_id)

        # 1. Create the initial anomaly node
        anomaly_node_id = self._generate_id(f"anomaly-{anomaly_id}")
        anomaly_node = EventNode(
            id=anomaly_node_id,
            event_type="hypothesis", # Starting with a hypothesis
            source="Supervisor",
            data={"description": anomaly_description, "trace_id": trace_id}
        )
        graph.add_node(anomaly_node)

        # 2. Analyze logs
        log_analysis_result = self.log_analyzer.analyze_trace(trace_id)

        if log_analysis_result.get("success"):
            # Create a node for the traceback
            tb_str = log_analysis_result["traceback"]
            tb_node_id = self._generate_id(tb_str)
            tb_node = EventNode(
                id=tb_node_id,
                event_type="traceback",
                source=log_analysis_result.get("file_path", "unknown_file"),
                data={
                    "traceback": tb_str,
                    "file_path": log_analysis_result.get("file_path"),
                    "line_number": log_analysis_result.get("line_number"),
                }
            )
            graph.add_node(tb_node)

            # Link the traceback to the initial anomaly
            edge = CausalEdge(
                source_id=tb_node_id,
                target_id=anomaly_node_id,
                relationship="provides_evidence_for",
                confidence=0.9
            )
            graph.add_edge(edge)

        # In the future, we would call other collectors here and add more nodes/edges.
        # For example:
        # git_findings = self.git_collector.analyze(file_path)
        # graph.add_node(...)
        # graph.add_edge(...)

        return graph

    @staticmethod
    def _generate_id(content: str) -> str:
        """Generates a deterministic SHA-256 hash for content to use as a node ID."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
