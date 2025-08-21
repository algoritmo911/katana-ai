from pydantic import BaseModel, Field
from typing import List, Dict, Any, Literal
from datetime import datetime

class EventNode(BaseModel):
    """
    Represents a single event or piece of evidence in the causal graph.
    """
    id: str = Field(..., description="A unique identifier for the event node (e.g., hash of content).")
    event_type: Literal["log", "commit", "metric", "traceback", "hypothesis"]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str = Field(..., description="The origin of the event (e.g., service name, file path).")
    data: Dict[str, Any] = Field(..., description="The payload of the event.")

class CausalEdge(BaseModel):
    """
    Represents a directed causal link between two event nodes.
    """
    source_id: str = Field(..., description="The ID of the source event node.")
    target_id: str = Field(..., description="The ID of the target event node.")
    relationship: str = Field(..., description="A description of the causal relationship (e.g., 'caused_by', 'related_to').")
    confidence: float = Field(default=1.0, description="The confidence score of this causal link (0.0 to 1.0).")

class CausalGraph(BaseModel):
    """
    Represents the full causal graph for an anomaly analysis.
    """
    anomaly_id: str = Field(..., description="A unique identifier for the anomaly being analyzed.")
    nodes: List[EventNode] = Field(default_factory=list)
    edges: List[CausalEdge] = Field(default_factory=list)

    def add_node(self, node: EventNode):
        """Adds a node to the graph, ensuring no duplicates."""
        if not any(n.id == node.id for n in self.nodes):
            self.nodes.append(node)

    def add_edge(self, edge: CausalEdge):
        """Adds an edge to the graph."""
        # Check if source and target nodes exist before adding
        source_exists = any(n.id == edge.source_id for n in self.nodes)
        target_exists = any(n.id == edge.target_id for n in self.nodes)
        if source_exists and target_exists:
            self.edges.append(edge)
        else:
            # In a real implementation, we might want to raise an error here
            print(f"Warning: Could not add edge. Node not found for source '{edge.source_id}' or target '{edge.target_id}'.")

    def get_node(self, node_id: str) -> EventNode | None:
        """Retrieves a node by its ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None
