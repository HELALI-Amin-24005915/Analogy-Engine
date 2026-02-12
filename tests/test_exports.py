"""Unit tests for report export functions (Markdown and PDF)."""

from core.schema import (
    ActionPlan,
    AnalogyMapping,
    ResearchReport,
    ValidatedHypothesis,
)


def _sample_report(*, with_sources: bool = False, with_action_plan: bool = True) -> ResearchReport:
    """Create a sample ResearchReport for testing."""
    mapping = AnalogyMapping(
        graph_a_id="hydraulics",
        graph_b_id="electronics",
        score=0.92,
        explanation="Strong structural mapping.",
    )
    hypothesis = ValidatedHypothesis(
        mapping=mapping,
        is_consistent=True,
        confidence=0.95,
    )
    ap = (
        ActionPlan(
            transferable_mechanisms=["PID control loop"],
            technical_roadmap=["Step 1: Define loss function", "Step 2: Implement feedback"],
            key_metrics_to_track=["latency p99"],
            potential_pitfalls=["oscillation in feedback loop"],
        )
        if with_action_plan
        else ActionPlan()
    )
    return ResearchReport(
        hypothesis=hypothesis,
        summary="Pressure maps to voltage; flow maps to current.",
        findings=["Ohm's law mirrors Hagen–Poiseuille", "Resistance = constriction"],
        recommendation="Explore PID-based control.",
        action_plan=ap,
        sources=["https://arxiv.org/example", "https://ieee.org/example"] if with_sources else [],
        input_query="hydraulics vs electronics",
    )


# ── Markdown Generation ───────────────────────────────────────


class TestGenerateMarkdown:
    def test_contains_title(self) -> None:
        from app import generate_markdown

        md = generate_markdown(_sample_report())
        assert "# Analogy Engine - Research Report" in md

    def test_contains_summary(self) -> None:
        from app import generate_markdown

        md = generate_markdown(_sample_report())
        assert "Pressure maps to voltage" in md

    def test_contains_findings(self) -> None:
        from app import generate_markdown

        md = generate_markdown(_sample_report())
        assert "Ohm's law mirrors Hagen–Poiseuille" in md

    def test_contains_action_plan(self) -> None:
        from app import generate_markdown

        md = generate_markdown(_sample_report(with_action_plan=True))
        assert "PID control loop" in md
        assert "Step 1: Define loss function" in md

    def test_no_sources_by_default(self) -> None:
        from app import generate_markdown

        md = generate_markdown(_sample_report(with_sources=True), include_sources=False)
        assert "arxiv.org" not in md

    def test_includes_sources_when_requested(self) -> None:
        from app import generate_markdown

        md = generate_markdown(_sample_report(with_sources=True), include_sources=True)
        assert "https://arxiv.org/example" in md

    def test_empty_action_plan_shows_na(self) -> None:
        from app import generate_markdown

        md = generate_markdown(_sample_report(with_action_plan=False))
        assert "N/A" in md


# ── PDF Generation ─────────────────────────────────────────────


class TestGeneratePDF:
    def test_returns_bytes(self) -> None:
        from app import generate_pdf

        pdf_bytes = generate_pdf(_sample_report())
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 100

    def test_pdf_header(self) -> None:
        from app import generate_pdf

        pdf_bytes = generate_pdf(_sample_report())
        # PDF files start with %PDF
        assert pdf_bytes[:5] == b"%PDF-"

    def test_with_sources(self) -> None:
        from app import generate_pdf

        pdf_bytes = generate_pdf(_sample_report(with_sources=True), include_sources=True)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 100


# ── ASCII sanitization ────────────────────────────────────────


class TestSanitizeForAscii:
    def test_ascii_unchanged(self) -> None:
        from app import _sanitize_for_ascii

        assert _sanitize_for_ascii("hello") == "hello"

    def test_unicode_replaced(self) -> None:
        from app import _sanitize_for_ascii

        result = _sanitize_for_ascii("café")
        assert result == "caf?"

    def test_empty(self) -> None:
        from app import _sanitize_for_ascii

        assert _sanitize_for_ascii("") == ""
