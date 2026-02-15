"""Unit tests for Triple-Layer Ontology: alignment check and schema (LogicNode, NodeMatch)."""

import pytest

from core.ontology import check_ontology_alignment
from core.schema import (
    AnalogyMapping,
    LogicalPropertyGraph,
    LogicNode,
    NodeMatch,
)

# ---------------------------------------------------------------------------
# Fixtures: graphs and mappings
# ---------------------------------------------------------------------------


@pytest.fixture
def graph_same_types() -> tuple[LogicalPropertyGraph, LogicalPropertyGraph]:
    """Two graphs with nodes that have matching ontology types (STRUCTURE/STRUCTURE, etc.)."""
    graph_a = LogicalPropertyGraph(
        nodes=[
            LogicNode(id="a1", label="Neuron", node_type="STRUCTURE"),
            LogicNode(id="a2", label="Spike", node_type="FUNCTION"),
            LogicNode(id="a3", label="Latency", node_type="ATTRIBUTE"),
        ],
        edges=[],
    )
    graph_b = LogicalPropertyGraph(
        nodes=[
            LogicNode(id="b1", label="Server", node_type="STRUCTURE"),
            LogicNode(id="b2", label="Packet", node_type="FUNCTION"),
            LogicNode(id="b3", label="Throughput", node_type="ATTRIBUTE"),
        ],
        edges=[],
    )
    return graph_a, graph_b


@pytest.fixture
def mapping_valid_alignment(
    graph_same_types: tuple[LogicalPropertyGraph, LogicalPropertyGraph],
) -> AnalogyMapping:
    """Node matches all same type: a1->b1 (STRUCTURE), a2->b2 (FUNCTION), a3->b3 (ATTRIBUTE)."""
    _, _ = graph_same_types
    return AnalogyMapping(
        graph_a_id="ga",
        graph_b_id="gb",
        node_matches=[
            NodeMatch(source_id="a1", target_id="b1", reasoning="both structure"),
            NodeMatch(source_id="a2", target_id="b2", reasoning="both function"),
            NodeMatch(source_id="a3", target_id="b3", reasoning="both attribute"),
        ],
        score=0.9,
        explanation="Valid alignment.",
    )


# ---------------------------------------------------------------------------
# check_ontology_alignment: valid alignment
# ---------------------------------------------------------------------------


def test_ontology_alignment_valid(
    graph_same_types: tuple[LogicalPropertyGraph, LogicalPropertyGraph],
    mapping_valid_alignment: AnalogyMapping,
) -> None:
    """When all node_matches align same node_type, check returns (True, [])."""
    graph_a, graph_b = graph_same_types
    ok, issues = check_ontology_alignment(mapping_valid_alignment, graph_a, graph_b)
    assert ok is True
    assert issues == []


# ---------------------------------------------------------------------------
# check_ontology_alignment: single mismatch
# ---------------------------------------------------------------------------


def test_ontology_alignment_single_mismatch(
    graph_same_types: tuple[LogicalPropertyGraph, LogicalPropertyGraph],
) -> None:
    """One pair STRUCTURE vs FUNCTION -> (False, one issue)."""
    graph_a, graph_b = graph_same_types
    mapping = AnalogyMapping(
        graph_a_id="ga",
        graph_b_id="gb",
        node_matches=[
            NodeMatch(source_id="a1", target_id="b2", reasoning="wrong"),  # STRUCTURE -> FUNCTION
            NodeMatch(source_id="a2", target_id="b2", reasoning="ok"),
        ],
        score=0.5,
        explanation="One mismatch.",
    )
    ok, issues = check_ontology_alignment(mapping, graph_a, graph_b)
    assert ok is False
    assert len(issues) == 1
    assert "STRUCTURE" in issues[0] and "FUNCTION" in issues[0]
    assert "a1" in issues[0] and "b2" in issues[0]


# ---------------------------------------------------------------------------
# check_ontology_alignment: multiple mismatches
# ---------------------------------------------------------------------------


def test_ontology_alignment_multiple_mismatches(
    graph_same_types: tuple[LogicalPropertyGraph, LogicalPropertyGraph],
) -> None:
    """Several pairs with type mismatch -> (False, multiple issues)."""
    graph_a, graph_b = graph_same_types
    mapping = AnalogyMapping(
        graph_a_id="ga",
        graph_b_id="gb",
        node_matches=[
            NodeMatch(source_id="a1", target_id="b2", reasoning="S->F"),
            NodeMatch(source_id="a2", target_id="b3", reasoning="F->A"),
            NodeMatch(source_id="a3", target_id="b1", reasoning="A->S"),
        ],
        score=0.3,
        explanation="All mismatched.",
    )
    ok, issues = check_ontology_alignment(mapping, graph_a, graph_b)
    assert ok is False
    assert len(issues) == 3


# ---------------------------------------------------------------------------
# check_ontology_alignment: missing node ids (skipped, no issue)
# ---------------------------------------------------------------------------


def test_ontology_alignment_missing_node_ids(
    graph_same_types: tuple[LogicalPropertyGraph, LogicalPropertyGraph],
) -> None:
    """When source_id or target_id is not in the graph, that pair is skipped (no issue)."""
    graph_a, graph_b = graph_same_types
    mapping = AnalogyMapping(
        graph_a_id="ga",
        graph_b_id="gb",
        node_matches=[
            NodeMatch(source_id="missing_a", target_id="b1", reasoning="?"),
            NodeMatch(source_id="a1", target_id="missing_b", reasoning="?"),
            NodeMatch(source_id="a2", target_id="b2", reasoning="ok"),  # only valid pair
        ],
        score=0.5,
        explanation="Missing ids.",
    )
    ok, issues = check_ontology_alignment(mapping, graph_a, graph_b)
    # Only a2->b2 is checked; a2 and b2 are both FUNCTION, so alignment is valid.
    assert ok is True
    assert issues == []


def test_ontology_alignment_missing_id_plus_mismatch(
    graph_same_types: tuple[LogicalPropertyGraph, LogicalPropertyGraph],
) -> None:
    """One pair missing, one pair mismatch -> one issue (the mismatch)."""
    graph_a, graph_b = graph_same_types
    mapping = AnalogyMapping(
        graph_a_id="ga",
        graph_b_id="gb",
        node_matches=[
            NodeMatch(source_id="ghost", target_id="b1", reasoning="skip"),
            NodeMatch(source_id="a1", target_id="b3", reasoning="S->A"),
        ],
        score=0.5,
        explanation="Mixed.",
    )
    ok, issues = check_ontology_alignment(mapping, graph_a, graph_b)
    assert ok is False
    assert len(issues) == 1
    assert "a1" in issues[0] and "b3" in issues[0]


# ---------------------------------------------------------------------------
# Schema: LogicNode accepts only STRUCTURE, FUNCTION, ATTRIBUTE
# ---------------------------------------------------------------------------


def test_logic_node_accepts_ontology_types() -> None:
    """LogicNode accepts node_type STRUCTURE, FUNCTION, ATTRIBUTE."""
    for t in ("STRUCTURE", "FUNCTION", "ATTRIBUTE"):
        n = LogicNode(id="x", label="y", node_type=t)
        assert n.node_type == t


def test_logic_node_default_type() -> None:
    """LogicNode defaults node_type to STRUCTURE."""
    n = LogicNode(id="x", label="y")
    assert n.node_type == "STRUCTURE"


def test_logic_node_rejects_invalid_type() -> None:
    """LogicNode with node_type not in (STRUCTURE, FUNCTION, ATTRIBUTE) is rejected by Pydantic."""
    with pytest.raises(Exception):  # ValidationError from Pydantic
        LogicNode(id="x", label="y", node_type="concept")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Schema: NodeMatch accepts source_ontology and target_ontology
# ---------------------------------------------------------------------------


def test_node_match_accepts_ontology_fields() -> None:
    """NodeMatch accepts optional source_ontology and target_ontology."""
    m = NodeMatch(
        source_id="a1",
        target_id="b1",
        reasoning="ok",
        source_ontology="STRUCTURE",
        target_ontology="STRUCTURE",
    )
    assert m.source_ontology == "STRUCTURE"
    assert m.target_ontology == "STRUCTURE"


def test_node_match_ontology_optional() -> None:
    """NodeMatch works without source_ontology/target_ontology (default None)."""
    m = NodeMatch(source_id="a1", target_id="b1", reasoning="ok")
    assert m.source_ontology is None
    assert m.target_ontology is None
