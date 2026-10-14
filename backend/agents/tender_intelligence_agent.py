"""End-to-end Member 1 workflow: discover tenders, then extract requirements.

Uses the local catalogue and its document_path values. This is an integration
baseline, not a live government-portal scraper or an eligibility decision.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from backend.agents.discovery_agent import DEFAULT_CATALOGUE, TenderDiscoveryAgent
from backend.agents.requirement_agent import TenderRequirementAgent
from backend.services.document_parser import extract_document

ROOT = Path(__file__).resolve().parents[2]


def _safe_document_path(raw_path: str, root: Path = ROOT) -> Path:
    """Resolve a catalogue document path without allowing traversal outside root."""
    candidate = (root / raw_path).resolve()
    resolved_root = root.resolve()
    if candidate != resolved_root and resolved_root not in candidate.parents:
        raise ValueError(f"Document path must stay inside project root: {raw_path}")
    return candidate


class TenderIntelligenceAgent:
    """Compose discovery and extraction into one Member 1 workflow."""

    def __init__(self, catalogue_path: str | Path = DEFAULT_CATALOGUE, root: str | Path = ROOT):
        self.root = Path(root).resolve()
        self.discovery = TenderDiscoveryAgent(catalogue_path)
        self.requirements = TenderRequirementAgent()

    def run(
        self,
        company_profile: dict[str, Any],
        limit: int = 10,
        min_score: float = 0.0,
        include_unmatched: bool = False,
    ) -> dict[str, Any]:
        """Return ranked tenders with extracted requirements and evidence.

        ``include_unmatched`` is explicit because a score of zero does not mean
        a tender is ineligible; it only means no exact lexical terms matched.
        """
        discovered = self.discovery.search(company_profile, limit=limit, min_score=min_score)
        results: list[dict[str, Any]] = []
        for item in discovered:
            document_path = item.get("document_path")
            if not document_path:
                if include_unmatched:
                    results.append(self._without_document(item, "No document_path is listed in the catalogue."))
                continue
            try:
                path = _safe_document_path(str(document_path), self.root)
                if not path.is_file():
                    results.append(self._without_document(item, f"Tender document not found: {document_path}"))
                    continue
                document = extract_document(path)
                extraction = self.requirements.extract(
                    document.text,
                    tender_id=str(item.get("tender_id") or item.get("id") or path.stem),
                    source_file=str(document.source_file),
                    document_warnings=list(document.warnings),
                )
                extraction["source_metadata"] = {
                    "file_type": document.file_type,
                    "page_count": document.page_count,
                    "character_count": document.character_count,
                    "sha256": document.sha256,
                }
                # Keep extraction fields at the top level for Member 2's
                # TenderRequirements.from_extraction(extraction) adapter.
                result = dict(extraction)
                result["discovery"] = {
                    "tender_id": item.get("tender_id"),
                    "title": item.get("title"),
                    "organization": item.get("organization"),
                    "location": item.get("location"),
                    "catalogue_deadline": item.get("deadline"),
                    "estimated_value": item.get("estimated_value"),
                    "categories": item.get("categories", []),
                    "source_url": item.get("source_url"),
                    "relevance_score": item.get("relevance_score", 0.0),
                    "matched_terms": item.get("matched_terms", []),
                    "discovery_note": item.get("discovery_note", ""),
                }
                # Retain a visible discrepancy if the catalogue and document differ.
                catalogue_deadline = str(item.get("deadline") or "").strip()
                extracted_deadline = str((extraction.get("normalized_requirements") or {}).get("bid_submission_deadline_iso") or "").strip()
                result["cross_checks"] = {
                    "catalogue_vs_document_deadline": {
                        "catalogue_deadline": catalogue_deadline or None,
                        "document_deadline": extracted_deadline or extraction.get("deadlines", {}).get("bid_submission_deadline"),
                        "status": (
                            "match" if catalogue_deadline and extracted_deadline and catalogue_deadline == extracted_deadline
                            else "review_required" if catalogue_deadline or extracted_deadline
                            else "not_available"
                        ),
                    }
                }
                results.append(result)
            except (OSError, ValueError) as exc:
                results.append(self._without_document(item, f"Could not process tender document: {exc}"))

        return {
            "schema_version": "1.0",
            "agent": "member1_tender_intelligence",
            "catalogue_mode": "local_catalogue",
            "company_profile_summary": {
                "industry": company_profile.get("industry"),
                "location": company_profile.get("location"),
                "keywords": company_profile.get("keywords", []),
            },
            "result_count": len(results),
            "results": results,
            "limitations": [
                "Discovery uses explainable keyword overlap; relevance is not eligibility.",
                "Only documents referenced by the local catalogue are processed.",
                "Requirement extraction is rule-based and requires human verification.",
                "This workflow does not poll live tender portals or automatically ingest corrigenda.",
            ],
        }

    @staticmethod
    def _without_document(item: dict[str, Any], warning: str) -> dict[str, Any]:
        return {
            "schema_version": "1.1",
            "tender_id": item.get("tender_id") or item.get("id"),
            "source_document": item.get("document_path"),
            "discovery": {
                "tender_id": item.get("tender_id"),
                "title": item.get("title"),
                "organization": item.get("organization"),
                "location": item.get("location"),
                "catalogue_deadline": item.get("deadline"),
                "source_url": item.get("source_url"),
                "relevance_score": item.get("relevance_score", 0.0),
                "matched_terms": item.get("matched_terms", []),
                "discovery_note": item.get("discovery_note", ""),
            },
            "eligibility": {},
            "technical_requirements": [],
            "financial_requirements": [],
            "certifications": [],
            "documents_required": [],
            "deadlines": {},
            "normalized_requirements": {},
            "evidence": {},
            "warnings": [warning, "Manual review required; no requirements were extracted."],
            "review_required": True,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover tenders and extract their requirements.")
    parser.add_argument("--profile", required=True, help="Path to a JSON company profile")
    parser.add_argument("--catalogue", default=str(DEFAULT_CATALOGUE), help="Tender catalogue JSON path")
    parser.add_argument("--limit", type=int, default=10, help="Maximum tenders to process")
    parser.add_argument("--min-score", type=float, default=0.0, help="Minimum lexical relevance score from 0 to 100")
    parser.add_argument("--output", required=True, help="Output JSON file")
    args = parser.parse_args()
    if args.limit < 0:
        parser.error("--limit must be zero or greater")
    if not 0 <= args.min_score <= 100:
        parser.error("--min-score must be between 0 and 100")
    profile_path = Path(args.profile)
    with profile_path.open("r", encoding="utf-8") as handle:
        profile = json.load(handle)
    if not isinstance(profile, dict):
        parser.error("Company profile JSON must be an object")
    result = TenderIntelligenceAgent(args.catalogue).run(profile, args.limit, args.min_score)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Processed {result['result_count']} tender(s); saved {output}")


if __name__ == "__main__":
    main()
