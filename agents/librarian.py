"""
Librarian Agent: Memory service for past ResearchReports.

Manages a local JSON database of stored reports and supports searching
for past analogies by similar logical structures or domains.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from core.schema import MemoryMetadata, ResearchReport


class Librarian:
    """
    Service that stores and retrieves ResearchReports in a JSON file.

    Not a pipeline filter; used by the orchestrator to persist reports
    and consult past analogies before running a new matching.
    """

    def __init__(self, memory_path: str = "data/memory.json") -> None:
        """
        Initialize the Librarian with the path to the memory file.

        Args:
            memory_path: Path to the JSON file (default: data/memory.json).
        """
        self._path = Path(memory_path)

    def _ensure_data_dir(self) -> None:
        """Create the parent directory of the memory file if it does not exist."""
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _load_memory(self) -> list[dict]:
        """Load memory entries from the JSON file. Returns [] if file is missing."""
        if not self._path.exists():
            return []
        try:
            text = self._path.read_text(encoding="utf-8")
            data = json.loads(text)
            if not isinstance(data, list):
                return []
            return data
        except (json.JSONDecodeError, OSError):
            return []

    def _save_memory(self, entries: list[dict]) -> None:
        """Write the list of entries to the JSON file."""
        self._ensure_data_dir()
        self._path.write_text(
            json.dumps(entries, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    def store_report(self, report: ResearchReport) -> None:
        """
        Save a new report to the database.

        Args:
            report: The ResearchReport to store.
        """
        entries = self._load_memory()
        metadata = MemoryMetadata(
            stored_at=datetime.now(timezone.utc),
            frequency=0,
        )
        entries.append(
            {
                "report": report.model_dump(mode="json"),
                "metadata": metadata.model_dump(mode="json"),
            }
        )
        self._save_memory(entries)

    def get_all_reports(self) -> list[tuple[ResearchReport, MemoryMetadata]]:
        """
        Return all stored reports with their metadata (for UI listing).

        Returns:
            List of (ResearchReport, MemoryMetadata) in storage order.
        """
        entries = self._load_memory()
        results: list[tuple[ResearchReport, MemoryMetadata]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            report_dict = entry.get("report")
            meta_dict = entry.get("metadata")
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

        Uses simple substring and keyword matching over summary, findings,
        recommendation, and the mapping explanation.

        Args:
            query_text: Search query (e.g. concatenated source and target text).

        Returns:
            List of (ResearchReport, MemoryMetadata) for matching entries.
        """
        entries = self._load_memory()
        if not query_text or not entries:
            return []

        query_lower = query_text.lower().strip()
        query_words = [w for w in query_lower.split() if w]

        results: list[tuple[ResearchReport, MemoryMetadata]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            report_dict = entry.get("report")
            meta_dict = entry.get("metadata")
            if not isinstance(report_dict, dict) or not isinstance(meta_dict, dict):
                continue
            try:
                report = ResearchReport.model_validate(report_dict)
                metadata = MemoryMetadata.model_validate(meta_dict)
            except Exception:
                continue

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
