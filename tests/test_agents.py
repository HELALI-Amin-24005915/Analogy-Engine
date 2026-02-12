"""Unit tests for agent response parsers (no LLM calls)."""

from core.schema import (
    ActionPlan,
    AnalogyMapping,
    LogicalPropertyGraph,
    ResearchReport,
    ValidatedHypothesis,
)

# ── Scout._parse_graph_response ───────────────────────────────


class TestScoutParser:
    """Test Scout._parse_graph_response without needing autogen."""

    def _parse(self, content: str) -> LogicalPropertyGraph:
        from agents.scout import Scout

        # Instantiate with dummy config; _parse_graph_response doesn't use LLM
        scout = object.__new__(Scout)
        return scout._parse_graph_response(content)

    def test_valid_json(self) -> None:
        raw = (
            '{"nodes": [{"id": "n1", "label": "Pressure", "node_type": "concept"}], '
            '"edges": [{"source": "n1", "target": "n1", "relation": "self"}]}'
        )
        graph = self._parse(raw)
        assert len(graph.nodes) == 1
        assert graph.nodes[0].label == "Pressure"

    def test_markdown_wrapped(self) -> None:
        raw = '```json\n{"nodes": [], "edges": []}\n```'
        graph = self._parse(raw)
        assert graph.nodes == []

    def test_empty_content(self) -> None:
        graph = self._parse("")
        assert graph.nodes == []
        assert graph.edges == []

    def test_invalid_json(self) -> None:
        graph = self._parse("not json at all")
        assert graph.nodes == []

    def test_pascal_case_conversion(self) -> None:
        raw = (
            '{"nodes": [{"id": "n1", "label": "information sharing", '
            '"node_type": "concept"}], "edges": []}'
        )
        graph = self._parse(raw)
        assert graph.nodes[0].label == "InformationSharing"


# ── Scout._to_pascal_case ─────────────────────────────────────


class TestScoutPascalCase:
    def _convert(self, s: str) -> str:
        from agents.scout import Scout

        return Scout._to_pascal_case(s)

    def test_basic(self) -> None:
        assert self._convert("hello world") == "HelloWorld"

    def test_underscores(self) -> None:
        assert self._convert("my_variable_name") == "MyVariableName"

    def test_single_word(self) -> None:
        assert self._convert("pressure") == "Pressure"

    def test_empty(self) -> None:
        assert self._convert("") == ""

    def test_already_pascal(self) -> None:
        assert self._convert("PascalCase") == "Pascalcase"


# ── Matcher._parse_mapping_response ───────────────────────────


class TestMatcherParser:
    """Test Matcher._parse_mapping_response without needing autogen."""

    def _parse(self, content: str) -> AnalogyMapping:
        from agents.matcher import Matcher

        matcher = object.__new__(Matcher)
        return matcher._parse_mapping_response(content, id_a="ga", id_b="gb")

    def test_valid_json(self) -> None:
        raw = (
            '{"graph_a_id": "ga", "graph_b_id": "gb", '
            '"node_matches": [{"source_id": "n1", "target_id": "n2", '
            '"reasoning": "Both are forces"}], '
            '"edge_mappings": [], "score": 0.85, '
            '"explanation": "Good analogy"}'
        )
        m = self._parse(raw)
        assert m.score == 0.85
        assert len(m.node_matches) == 1

    def test_empty_content(self) -> None:
        m = self._parse("")
        assert m.score == 0.0
        assert m.explanation == "Failed to parse Matcher response."

    def test_markdown_wrapped(self) -> None:
        raw = (
            "```json\n"
            '{"graph_a_id": "ga", "graph_b_id": "gb", '
            '"node_matches": [], "edge_mappings": [], '
            '"score": 0.5, "explanation": "test"}\n'
            "```"
        )
        m = self._parse(raw)
        assert m.score == 0.5

    def test_invalid_edge_mappings_sanitized(self) -> None:
        raw = (
            '{"graph_a_id": "ga", "graph_b_id": "gb", '
            '"node_matches": [], '
            '"edge_mappings": [{"invalid": true}], '
            '"score": 0.7, "explanation": "test"}'
        )
        m = self._parse(raw)
        assert m.edge_mappings == []


# ── Critic._parse_response ────────────────────────────────────


class TestCriticParser:
    """Test Critic._parse_response without needing autogen."""

    def _parse(self, content: str, mapping: AnalogyMapping) -> ValidatedHypothesis:
        from agents.critic import Critic

        critic = object.__new__(Critic)
        return critic._parse_response(content, mapping)

    def _mapping(self) -> AnalogyMapping:
        return AnalogyMapping(graph_a_id="ga", graph_b_id="gb", score=0.9)

    def test_valid_response(self) -> None:
        raw = '{"is_consistent": true, "issues": [], "confidence": 0.92}'
        h = self._parse(raw, self._mapping())
        assert h.is_consistent is True
        assert h.confidence == 0.92
        assert h.issues == []

    def test_issues_present(self) -> None:
        raw = '{"is_consistent": false, "issues": ["Role mismatch"], "confidence": 0.3}'
        h = self._parse(raw, self._mapping())
        assert not h.is_consistent
        assert h.issues == ["Role mismatch"]

    def test_empty_returns_fallback(self) -> None:
        h = self._parse("", self._mapping())
        assert h.confidence == 0.0
        assert "fallback" in str(h.properties)


# ── Architect._parse_response ─────────────────────────────────


class TestArchitectParser:
    """Test Architect._parse_response without needing autogen."""

    def _hypothesis(self) -> ValidatedHypothesis:
        mapping = AnalogyMapping(graph_a_id="ga", graph_b_id="gb", score=0.9)
        return ValidatedHypothesis(mapping=mapping, is_consistent=True, confidence=0.9)

    def _parse(self, content: str) -> ResearchReport:
        from agents.architect import Architect

        architect = object.__new__(Architect)
        return architect._parse_response(content, self._hypothesis())

    def test_valid_report(self) -> None:
        raw = (
            '{"summary": "Great analogy", "findings": ["F1", "F2"], '
            '"recommendation": "Proceed", "action_plan": {'
            '"transferable_mechanisms": ["PID"], '
            '"technical_roadmap": ["Step 1"], '
            '"key_metrics_to_track": ["latency"], '
            '"potential_pitfalls": ["oscillation"]}}'
        )
        report = self._parse(raw)
        assert report.summary == "Great analogy"
        assert len(report.findings) == 2
        assert report.action_plan.transferable_mechanisms == ["PID"]

    def test_empty_returns_fallback(self) -> None:
        report = self._parse("")
        assert "failed" in report.summary.lower()

    def test_markdown_wrapped(self) -> None:
        raw = (
            "```json\n"
            '{"summary": "test", "findings": [], '
            '"recommendation": "ok", "action_plan": {}}\n'
            "```"
        )
        report = self._parse(raw)
        assert report.summary == "test"

    def test_missing_action_plan(self) -> None:
        raw = '{"summary": "s", "findings": ["f"], "recommendation": "r"}'
        report = self._parse(raw)
        assert isinstance(report.action_plan, ActionPlan)
        assert report.action_plan.transferable_mechanisms == []
