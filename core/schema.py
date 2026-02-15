"""
Canonical data contracts for the Pipe and Filter pipeline.

All data flowing between filters (Scout -> Matcher -> Critic -> Architect)
is strictly typed with Pydantic V2 models. The Triple-Layer Ontology
(STRUCTURE, FUNCTION, ATTRIBUTE) is enforced via LogicNode.node_type and
NodeMatch.source_ontology/target_ontology.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# Triple-Layer Ontology: only these node types are valid for alignment.
NodeTypeLiteral = Literal["STRUCTURE", "FUNCTION", "ATTRIBUTE"]


class LogicNode(BaseModel):
    """Single node in a logical property graph (Scout output).

    Each node has an ontological type (Triple-Layer): STRUCTURE, FUNCTION, or
    ATTRIBUTE. Used in LogicalPropertyGraph for alignment by the Matcher.
    """

    id: str = Field(..., description="Unique identifier for the node.")
    label: str = Field(..., description="Human-readable label.")
    node_type: NodeTypeLiteral = Field(
        default="STRUCTURE",
        description="Ontological type: STRUCTURE (What), FUNCTION (How), or ATTRIBUTE (Cost/Value).",
    )
    properties: dict[str, Any] = Field(default_factory=dict, description="Optional metadata.")


class LogicEdge(BaseModel):
    """Directed edge between two logic nodes.

    Represents a logical relation (e.g. causes, enables) between two nodes
    in a LogicalPropertyGraph.
    """

    source: str = Field(..., description="Id of the source node.")
    target: str = Field(..., description="Id of the target node.")
    relation: str = Field(..., description="Type of logical relation.")
    properties: dict[str, Any] = Field(default_factory=dict, description="Optional metadata.")


class LogicalPropertyGraph(BaseModel):
    """Graph of logical structures extracted from text (Scout output).

    Pipeline contract: Scout produces one graph per domain; Matcher consumes
    two graphs and produces AnalogyMapping.
    """

    nodes: list[LogicNode] = Field(default_factory=list, description="Nodes of the graph.")
    edges: list[LogicEdge] = Field(default_factory=list, description="Edges of the graph.")


class NodeMatch(BaseModel):
    """Matches a node from the source graph to a node in the target graph.

    For Triple-Layer alignment, source_ontology and target_ontology must be
    identical (STRUCTURE<->STRUCTURE, FUNCTION<->FUNCTION, ATTRIBUTE<->ATTRIBUTE).
    """

    source_id: str = Field(..., description="ID of the node in Graph A.")
    target_id: str = Field(..., description="ID of the node in Graph B.")
    reasoning: str = Field(..., description="Why these two nodes are functionally equivalent.")
    source_ontology: str | None = Field(
        default=None,
        description="Ontological type of source node (STRUCTURE/FUNCTION/ATTRIBUTE). Must equal target_ontology.",
    )
    target_ontology: str | None = Field(
        default=None,
        description="Ontological type of target node (STRUCTURE/FUNCTION/ATTRIBUTE). Must equal source_ontology.",
    )


class AnalogyMapping(BaseModel):
    """Result of matching two logical graphs (Matcher output).

    Contains node_matches (with source_ontology/target_ontology per pair),
    a global explanation, and a confidence score. Consumed by Critic and
    optionally by Matcher again during refinement.
    """

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
    """Analogy mapping plus verification result (Critic output).

    Indicates whether the mapping is consistent, lists issues (e.g. ontology
    mismatches), and provides a confidence score. Used to decide refinement
    and passed to Architect when accepted.
    """

    mapping: AnalogyMapping = Field(..., description="The analogy mapping under validation.")
    is_consistent: bool = Field(..., description="Whether the analogy is logically consistent.")
    issues: list[str] = Field(default_factory=list, description="List of detected issues.")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Validation confidence.")
    properties: dict[str, Any] = Field(default_factory=dict, description="Optional metadata.")


class ActionPlan(BaseModel):
    """Engineering action plan: transferable mechanisms, roadmap, metrics, pitfalls.

    Part of ResearchReport. Guides implementation from Source to Target domain
    (ontology-aware: signal/state adapters, decoupling).
    """

    transferable_mechanisms: list[str] = Field(
        default_factory=list,
        description="Specific algorithms or logic to copy from Source to Target.",
    )
    technical_roadmap: list[str] = Field(
        default_factory=list,
        description="Step-by-step implementation guide.",
    )
    key_metrics_to_track: list[str] = Field(
        default_factory=list,
        description="KPIs to measure success.",
    )
    potential_pitfalls: list[str] = Field(
        default_factory=list,
        description="Technical risks.",
    )


class ResearchReport(BaseModel):
    """Synthesis report (Architect output).

    Combines the validated hypothesis, summary, findings, recommendation, and
    action plan. Stored by Librarian and displayed in the UI.
    """

    hypothesis: ValidatedHypothesis = Field(..., description="The validated hypothesis.")
    summary: str = Field(default="", description="Executive summary.")
    findings: list[str] = Field(default_factory=list, description="Key findings.")
    recommendation: str = Field(default="", description="Research recommendation.")
    action_plan: ActionPlan = Field(
        default_factory=ActionPlan,
        description="Engineering action plan for implementation.",
    )
    sources: list[str] = Field(
        default_factory=list,
        description="List of source URLs collected during research.",
    )
    input_query: str = Field(
        default="",
        description="Original search query (domains or problem) entered by the user.",
    )
    properties: dict[str, Any] = Field(default_factory=dict, description="Optional metadata.")


class MemoryMetadata(BaseModel):
    """Metadata for a stored analogy report (Librarian memory).

    Tracks when the report was stored and how often it was retrieved.
    Returned with ResearchReport by get_all_reports and search_analogies.
    """

    stored_at: datetime = Field(..., description="When the report was stored.")
    frequency: int = Field(
        default=0, ge=0, description="How often this entry was retrieved or used."
    )
