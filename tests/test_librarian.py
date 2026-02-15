"""Unit tests for Librarian agent (with mocked MongoDB)."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId

from core.schema import MemoryMetadata, ResearchReport


@pytest.fixture
def mock_mongo_collection() -> MagicMock:
    coll = MagicMock()
    return coll


@pytest.fixture
def sample_report_dict() -> dict[str, Any]:
    return {
        "hypothesis": {
            "mapping": {
                "graph_a_id": "a",
                "graph_b_id": "b",
                "node_matches": [],
                "edge_mappings": [],
                "score": 0.9,
                "explanation": "Test",
                "properties": {},
            },
            "is_consistent": True,
            "issues": [],
            "confidence": 0.9,
            "properties": {},
        },
        "summary": "Test summary",
        "findings": ["Finding 1"],
        "recommendation": "Test recommendation",
        "action_plan": {
            "transferable_mechanisms": [],
            "technical_roadmap": [],
            "key_metrics_to_track": [],
            "potential_pitfalls": [],
        },
        "sources": [],
        "input_query": "source | target",
        "properties": {},
    }


@pytest.fixture
def sample_metadata_dict() -> dict[str, Any]:
    return {
        "stored_at": "2025-01-01T12:00:00Z",
        "frequency": 0,
    }


def test_delete_report_returns_true_when_deleted(
    mock_mongo_collection: MagicMock,
    sample_report_dict: dict[str, Any],
    sample_metadata_dict: dict[str, Any],
) -> None:
    mock_mongo_collection.delete_one.return_value.deleted_count = 1
    with patch("agents.librarian.MongoClient"), patch("agents.librarian.get_config") as mock_config:
        mock_config.return_value.MONGODB_URI = "mongodb://localhost"
        from agents.librarian import Librarian

        lib = Librarian()
        lib._collection = mock_mongo_collection
        doc_id = ObjectId()
        result = lib.delete_report(doc_id)
        assert result is True
        mock_mongo_collection.delete_one.assert_called_once_with({"_id": doc_id})


def test_delete_report_returns_false_when_nothing_deleted(
    mock_mongo_collection: MagicMock,
) -> None:
    mock_mongo_collection.delete_one.return_value.deleted_count = 0
    with patch("agents.librarian.MongoClient"), patch("agents.librarian.get_config") as mock_config:
        mock_config.return_value.MONGODB_URI = "mongodb://localhost"
        from agents.librarian import Librarian

        lib = Librarian()
        lib._collection = mock_mongo_collection
        doc_id = ObjectId()
        result = lib.delete_report(doc_id)
        assert result is False


def test_get_all_reports_returns_tuples_of_report_metadata_and_id(
    mock_mongo_collection: MagicMock,
    sample_report_dict: dict[str, Any],
    sample_metadata_dict: dict[str, Any],
) -> None:
    doc_id = ObjectId()
    mock_mongo_collection.find.return_value.sort.return_value = [
        {
            "_id": doc_id,
            "report": sample_report_dict,
            "metadata": sample_metadata_dict,
        }
    ]
    with patch("agents.librarian.MongoClient"), patch("agents.librarian.get_config") as mock_config:
        mock_config.return_value.MONGODB_URI = "mongodb://localhost"
        from agents.librarian import Librarian

        lib = Librarian()
        lib._collection = mock_mongo_collection
        results = lib.get_all_reports()
        assert len(results) == 1
        report, metadata, rid = results[0]
        assert isinstance(report, ResearchReport)
        assert isinstance(metadata, MemoryMetadata)
        assert rid == doc_id
        assert report.input_query == "source | target"
        assert report.hypothesis.confidence == 0.9
