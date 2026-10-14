
"""Tender source adapter interface.

For a reliable classroom demo, discovery reads a local JSON catalogue.
This file defines the interface for adding an approved public tender source.
Do not bypass CAPTCHAs, logins, access controls, or portal terms of use.
"""
from __future__ import annotations
from typing import Any, Protocol


class TenderSource(Protocol):
    def fetch_tenders(self, query: str = "") -> list[dict[str, Any]]:
        """Return normalized tender records using the schema in README.md."""
        ...


class JsonTenderSource:
    """Simple source implementation backed by a JSON catalogue."""
    def __init__(self, catalogue_path: str):
        self.catalogue_path = catalogue_path

    def fetch_tenders(self, query: str = "") -> list[dict[str, Any]]:
        import json
        from pathlib import Path

        path = Path(self.catalogue_path)
        with path.open("r", encoding="utf-8") as handle:
            tenders = json.load(handle)
        if not query.strip():
            return tenders
        query_terms = set(query.lower().split())
        return [
            tender for tender in tenders
            if query_terms & set(
                (str(tender.get("title", "")) + " " +
                 str(tender.get("description", ""))).lower().split()
            )
        ]
