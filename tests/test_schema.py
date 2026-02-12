"""Unit tests for core.schema Pydantic models."""

import pytest
from pydantic import ValidationError

from core.schema import (
    ActionPlan,
    AnalogyMapping,
    LogicalPropertyGraph,
    LogicEdge,
    LogicNode,
    MemoryMetadata,
    NodeMatch,
    ResearchReport,
    ValidatedHypothesis,
)

# ── LogicNode ──────────────────────────────────────────────────


class TestLogicNode:
    def test_create_minimal(self) -> None:
        node = LogicNode(id="n1", label="Pressure")
        assert node.id == "n1"
        assert node.label == "Pressure"
        assert node.node_type == "concept"
        assert node.properties == {}

    def test_create_full(self) -> None:
        node = LogicNode(
            id="n2",
            label="Flow",
            node_type="process",
            properties={"unit": "m³/s"},
        )
        assert node.node_type == "process"
        assert node.properties["unit"] == "m³/s"

    def test_missing_required_fields(self) -> None:
        with pytest.raises(ValidationError):
            LogicNode()  # type: ignore[call-arg]


# ── LogicEdge ──────────────────────────────────────────────────


class TestLogicEdge:
    def test_create(self) -> None:
        edge = LogicEdge(source="n1", target="n2", relation="causes")
        assert edge.source == "n1"
        assert edge.target == "n2"
        assert edge.relation == "causes"

    def test_missing_relation(self) -> None:
        with pytest.raises(ValidationError):
            LogicEdge(source="n1", target="n2")  # type: ignore[call-arg]


# ── LogicalPropertyGraph ──────────────────────────────────────


class TestLogicalPropertyGraph:
    def test_empty_graph(self) -> None:
        graph = LogicalPropertyGraph()
        assert graph.nodes == []
        assert graph.edges == []

    def test_graph_with_nodes_and_edges(self) -> None:
        graph = LogicalPropertyGraph(
            nodes=[
                LogicNode(id="n1", label="Pressure"),
                LogicNode(id="n2", label="Flow"),
            ],
            edges=[LogicEdge(source="n1", target="n2", relation="causes")],
        )
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1
        assert graph.edges[0].relation == "causes"

    def test_roundtrip_serialization(self) -> None:
        graph = LogicalPropertyGraph(
            nodes=[LogicNode(id="x", label="X")],
            edges=[],
        )
        data = graph.model_dump(mode="json")
        restored = LogicalPropertyGraph.model_validate(data)
        assert restored.nodes[0].id == "x"


# ── NodeMatch ─────────────────────────────────────────────────


class TestNodeMatch:
    def test_create(self) -> None:
        nm = NodeMatch(
            source_id="a1",
            target_id="b1",
            reasoning="Both are driving forces.",
        )
        assert nm.source_id == "a1"
        assert nm.reasoning == "Both are driving forces."


# ── AnalogyMapping ─────────────────────────────────────────────


class TestAnalogyMapping:
    def test_defaults(self) -> None:
        m = AnalogyMapping(graph_a_id="ga", graph_b_id="gb")
        assert m.score == 0.0
        assert m.node_matches == []
        assert m.edge_mappings == []

    def test_score_bounds(self) -> None:
        with pytest.raises(ValidationError):
            AnalogyMapping(graph_a_id="ga", graph_b_id="gb", score=1.5)

    def test_score_lower_bound(self) -> None:
        with pytest.raises(ValidationError):
            AnalogyMapping(graph_a_id="ga", graph_b_id="gb", score=-0.1)


# ── ValidatedHypothesis ────────────────────────────────────────


class TestValidatedHypothesis:
    @pytest.fixture()
    def mapping(self) -> AnalogyMapping:
        return AnalogyMapping(
            graph_a_id="ga",
            graph_b_id="gb",
            score=0.9,
        )

    def test_consistent(self, mapping: AnalogyMapping) -> None:
        h = ValidatedHypothesis(
            mapping=mapping,
            is_consistent=True,
            confidence=0.95,
        )
        assert h.is_consistent is True
        assert h.issues == []

    def test_with_issues(self, mapping: AnalogyMapping) -> None:
        h = ValidatedHypothesis(
            mapping=mapping,
            is_consistent=False,
            issues=["Role mismatch on node n2"],
            confidence=0.4,
        )
        assert not h.is_consistent
        assert len(h.issues) == 1


# ── ActionPlan ────────────────────────────────────────────────


class TestActionPlan:
    def test_defaults(self) -> None:
        ap = ActionPlan()
        assert ap.transferable_mechanisms == []
        assert ap.technical_roadmap == []
        assert ap.key_metrics_to_track == []
        assert ap.potential_pitfalls == []

    def test_full(self) -> None:
        ap = ActionPlan(
            transferable_mechanisms=["PID control loop"],
            technical_roadmap=["Step 1: define loss"],
            key_metrics_to_track=["latency p99"],
            potential_pitfalls=["oscillation"],
        )
        assert len(ap.transferable_mechanisms) == 1


# ── ResearchReport ─────────────────────────────────────────────


class TestResearchReport:
    @pytest.fixture()
    def hypothesis(self) -> ValidatedHypothesis:
        mapping = AnalogyMapping(graph_a_id="ga", graph_b_id="gb", score=0.9)
        return ValidatedHypothesis(mapping=mapping, is_consistent=True, confidence=0.95)

    def test_minimal(self, hypothesis: ValidatedHypothesis) -> None:
        report = ResearchReport(hypothesis=hypothesis)
        assert report.summary == ""
        assert report.findings == []
        assert report.sources == []

    def test_full_roundtrip(self, hypothesis: ValidatedHypothesis) -> None:
        report = ResearchReport(
            hypothesis=hypothesis,
            summary="The analogy holds.",
            findings=["Pressure maps to Voltage"],
            recommendation="Explore further.",
            action_plan=ActionPlan(
                transferable_mechanisms=["PID loop"],
            ),
            sources=["https://example.com"],
            input_query="hydraulics vs electronics",
        )
        data = report.model_dump(mode="json")
        restored = ResearchReport.model_validate(data)
        assert restored.summary == "The analogy holds."
        assert restored.sources == ["https://example.com"]
        assert restored.action_plan.transferable_mechanisms == ["PID loop"]


# ── MemoryMetadata ─────────────────────────────────────────────


class TestMemoryMetadata:
    def test_create(self) -> None:
        from datetime import datetime, timezone

        meta = MemoryMetadata(stored_at=datetime.now(timezone.utc))
        assert meta.frequency == 0

    def test_frequency_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            MemoryMetadata(
                stored_at="2024-01-01T00:00:00Z",  # type: ignore[arg-type]
                frequency=-1,
            )
