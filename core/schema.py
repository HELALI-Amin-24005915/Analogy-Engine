"""
Canonical data contracts for the Pipe and Filter pipeline.

All data flowing between filters (Scout -> Matcher -> Critic -> Architect)
is strictly typed with Pydantic V2 models.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LogicNode(BaseModel):
    """Single node in a logical property graph."""

    id: str = Field(..., description="Unique identifier for the node.")
    label: str = Field(..., description="Human-readable label.")
    node_type: str = Field(default="concept", description="Type of logical entity.")
    properties: dict[str, Any] = Field(default_factory=dict, description="Optional metadata.")


class LogicEdge(BaseModel):
    """Directed edge between two logic nodes."""

    source: str = Field(..., description="Id of the source node.")
    target: str = Field(..., description="Id of the target node.")
    relation: str = Field(..., description="Type of logical relation.")
    properties: dict[str, Any] = Field(default_factory=dict, description="Optional metadata.")


class LogicalPropertyGraph(BaseModel):
    """Graph of logical structures extracted from text (Scout output)."""

    nodes: list[LogicNode] = Field(default_factory=list, description="Nodes of the graph.")
    edges: list[LogicEdge] = Field(default_factory=list, description="Edges of the graph.")


class NodeMatch(BaseModel):
    """Matches a node from the source graph to a node in the target graph."""

    source_id: str = Field(..., description="ID of the node in Graph A.")
    target_id: str = Field(..., description="ID of the node in Graph B.")
    reasoning: str = Field(..., description="Why these two nodes are functionally equivalent.")


class AnalogyMapping(BaseModel):
    """Result of matching two logical graphs (Matcher output)."""

    graph_a_id: str = Field(..., description="Identifier for the first graph.")
    graph_b_id: str = Field(..., description="Identifier for the second graph.")
    node_matches: list[NodeMatch] = Field(
        default_factory=list, description="List of node pairs with reasoning."
    )
    edge_mappings: list[tuple[str, str]] = Field(
        default_factory=list,
        description="Pairs (edge_id_in_a, edge_id_in_b) or (source:target, source:target).",
    )
    score: float = Field(default=0.0, ge=0.0, le=1.0, description="Similarity or confidence score.")
    explanation: str = Field(default="", description="Global summary of the analogy.")
    properties: dict[str, Any] = Field(default_factory=dict, description="Optional metadata.")


class ValidatedHypothesis(BaseModel):
    """Analogy mapping plus verification result (Critic output)."""

    mapping: AnalogyMapping = Field(..., description="The analogy mapping under validation.")
    is_consistent: bool = Field(..., description="Whether the analogy is logically consistent.")
    issues: list[str] = Field(default_factory=list, description="List of detected issues.")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Validation confidence.")
    properties: dict[str, Any] = Field(default_factory=dict, description="Optional metadata.")


class ResearchReport(BaseModel):
    """Synthesis report (Architect output)."""

    hypothesis: ValidatedHypothesis = Field(..., description="The validated hypothesis.")
    summary: str = Field(default="", description="Executive summary.")
    findings: list[str] = Field(default_factory=list, description="Key findings.")
    recommendation: str = Field(default="", description="Research recommendation.")
    properties: dict[str, Any] = Field(default_factory=dict, description="Optional metadata.")


class MemoryMetadata(BaseModel):
    """Metadata for a stored analogy report (Librarian memory)."""

    stored_at: datetime = Field(..., description="When the report was stored.")
    frequency: int = Field(
        default=0, ge=0, description="How often this entry was retrieved or used."
    )
