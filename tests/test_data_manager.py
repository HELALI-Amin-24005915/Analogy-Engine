"""Unit tests for data_manager module."""

from core.schema import ResearchReport
from data_manager import EXISTING_DATA, get_existing_data


def test_existing_data_is_non_empty_list() -> None:
    assert isinstance(EXISTING_DATA, list)
    assert len(EXISTING_DATA) >= 2


def test_existing_data_items_have_required_keys() -> None:
    required = {
        "input_query",
        "summary",
        "findings",
        "recommendation",
        "action_plan",
        "confidence",
        "stored_at",
        "sources",
    }
    for item in EXISTING_DATA:
        assert isinstance(item, dict)
        for key in required:
            assert key in item, f"Missing key: {key}"


def test_existing_data_action_plan_structure() -> None:
    for item in EXISTING_DATA:
        ap = item["action_plan"]
        assert "transferable_mechanisms" in ap
        assert "technical_roadmap" in ap
        assert "key_metrics_to_track" in ap
        assert "potential_pitfalls" in ap
        assert isinstance(ap["transferable_mechanisms"], list)
        assert isinstance(ap["technical_roadmap"], list)


def test_get_existing_data_returns_list_of_research_reports() -> None:
    reports = get_existing_data()
    assert isinstance(reports, list)
    assert len(reports) == len(EXISTING_DATA)
    for r in reports:
        assert isinstance(r, ResearchReport)


def test_get_existing_data_report_has_hypothesis_and_confidence() -> None:
    reports = get_existing_data()
    for r in reports:
        assert hasattr(r, "hypothesis")
        assert 0 <= r.hypothesis.confidence <= 1
        assert hasattr(r, "summary")
        assert hasattr(r, "findings")
        assert hasattr(r, "action_plan")


def test_get_existing_data_ids_are_consistent() -> None:
    reports = get_existing_data()
    for i, (raw, report) in enumerate(zip(EXISTING_DATA, reports)):
        assert report.input_query == raw["input_query"]
        assert report.hypothesis.confidence == raw["confidence"]
        assert report.summary == raw["summary"]
