"""
Librarian Agent: Memory service for past ResearchReports.

Manages storage and retrieval of reports via MongoDB Atlas.
"""

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from core.config import get_config
from core.schema import MemoryMetadata, ResearchReport


class Librarian:
    """
    Memory service for ResearchReports (no ontology logic).

    Connects to MongoDB (analogy_engine database, reports collection).
    Stores and retrieves reports for the Knowledge Base UI; does not
    depend on Triple-Layer Ontology.
    """

    DB_NAME = "analogy_engine"
    COLLECTION_NAME = "reports"

    def __init__(self) -> None:
        """Initialize the Librarian with MongoDB connection from config.

        Raises:
            RuntimeError: If MongoDB connection fails (MONGODB_URI or network).
        """
        config = get_config()
        try:
            self._client: MongoClient[Any] = MongoClient(
                config.MONGODB_URI,
                tlsAllowInvalidCertificates=True,
                serverSelectionTimeoutMS=5000,
            )
        except Exception as e:
            raise RuntimeError(
                f"MongoDB connection failed (check MONGODB_URI and network/SSL): {e}"
            ) from e
        self._db: Database[Any] = self._client[self.DB_NAME]
        self._collection: Collection[Any] = self._db[self.COLLECTION_NAME]

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

    def get_all_reports(
        self,
    ) -> list[tuple[ResearchReport, MemoryMetadata, ObjectId]]:
        """
        Return all stored reports with their metadata and document id (for UI listing and delete).

        Returns:
            List of (ResearchReport, MemoryMetadata, doc_id) sorted by stored_at descending.
        """
        cursor = self._collection.find().sort("metadata.stored_at", -1)
        results: list[tuple[ResearchReport, MemoryMetadata, ObjectId]] = []
        for doc in cursor:
            report_dict = doc.get("report")
            meta_dict = doc.get("metadata")
            doc_id = doc.get("_id")
            if not isinstance(report_dict, dict) or not isinstance(meta_dict, dict):
                continue
            if doc_id is None:
                continue
            try:
                report = ResearchReport.model_validate(report_dict)
                metadata = MemoryMetadata.model_validate(meta_dict)
                results.append((report, metadata, doc_id))
            except Exception:
                continue
        return results

    def delete_report(self, doc_id: ObjectId) -> bool:
        """Delete a report by its MongoDB document id.

        Args:
            doc_id: MongoDB ObjectId of the document to delete.

        Returns:
            True if a document was deleted, False otherwise.
        """
        result = self._collection.delete_one({"_id": doc_id})
        return result.deleted_count > 0

    def search_analogies(
        self, query_text: str
    ) -> list[tuple[ResearchReport, MemoryMetadata, ObjectId]]:
        """
        Find past analogies that share similar logical structures or domains.

        Uses simple text search over summary, findings, recommendation, and mapping explanation.

        Args:
            query_text: Search query (e.g. concatenated source and target text).

        Returns:
            List of (ResearchReport, MemoryMetadata, doc_id) for matching entries.
        """
        all_reports = self.get_all_reports()
        if not query_text:
            return []

        query_lower = query_text.lower().strip()
        query_words = [w for w in query_lower.split() if w]

        results: list[tuple[ResearchReport, MemoryMetadata, ObjectId]] = []
        for report, metadata, doc_id in all_reports:
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
                results.append((report, metadata, doc_id))

        return results
