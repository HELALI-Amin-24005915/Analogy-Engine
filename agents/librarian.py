"""
Librarian Agent: Memory service for past ResearchReports.

Manages storage and retrieval of reports via MongoDB Atlas.
"""

from datetime import datetime, timezone

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from core.config import get_config
from core.schema import MemoryMetadata, ResearchReport


class Librarian:
    """
    Service that stores and retrieves ResearchReports in MongoDB.

    Connects to the analogy_engine database and the reports collection.
    """

    DB_NAME = "analogy_engine"
    COLLECTION_NAME = "reports"

    def __init__(self) -> None:
        """Initialize the Librarian with MongoDB connection from config."""
        config = get_config()
        self._client = MongoClient(config.MONGODB_URI)
        self._db: Database = self._client[self.DB_NAME]
        self._collection: Collection = self._db[self.COLLECTION_NAME]

    def store_report(self, report: ResearchReport) -> None:
        """
        Save a new report to MongoDB.

        Args:
            report: The ResearchReport to store.
        """
        metadata = MemoryMetadata(
            stored_at=datetime.now(timezone.utc),
            frequency=0,
        )
        document = {
            "report": report.model_dump(mode="json"),
            "metadata": metadata.model_dump(mode="json"),
        }
        self._collection.insert_one(document)

    def get_all_reports(self) -> list[tuple[ResearchReport, MemoryMetadata]]:
        """
        Return all stored reports with their metadata (for UI listing).

        Returns:
            List of (ResearchReport, MemoryMetadata) sorted by stored_at descending.
        """
        cursor = self._collection.find().sort("metadata.stored_at", -1)
        results: list[tuple[ResearchReport, MemoryMetadata]] = []
        for doc in cursor:
            report_dict = doc.get("report")
            meta_dict = doc.get("metadata")
            if not isinstance(report_dict, dict) or not isinstance(meta_dict, dict):
                continue
            try:
                report = ResearchReport.model_validate(report_dict)
                metadata = MemoryMetadata.model_validate(meta_dict)
                results.append((report, metadata))
            except Exception:
                continue
        return results

    def search_analogies(self, query_text: str) -> list[tuple[ResearchReport, MemoryMetadata]]:
        """
        Find past analogies that share similar logical structures or domains.

        Uses simple text search over summary, findings, recommendation, and mapping explanation.

        Args:
            query_text: Search query (e.g. concatenated source and target text).

        Returns:
            List of (ResearchReport, MemoryMetadata) for matching entries.
        """
        all_reports = self.get_all_reports()
        if not query_text:
            return []

        query_lower = query_text.lower().strip()
        query_words = [w for w in query_lower.split() if w]

        results: list[tuple[ResearchReport, MemoryMetadata]] = []
        for report, metadata in all_reports:
            searchable_parts = [
                report.summary or "",
                report.recommendation or "",
                (report.hypothesis.mapping.explanation or ""),
            ]
            searchable_parts.extend(report.findings or [])
            searchable = " ".join(searchable_parts).lower()

            matches = False
            if query_lower in searchable:
                matches = True
            elif query_words:
                for word in query_words:
                    if word in searchable:
                        matches = True
                        break

            if matches:
                results.append((report, metadata))

        return results
