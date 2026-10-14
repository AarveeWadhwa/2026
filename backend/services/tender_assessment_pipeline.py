"""Integrate Member 1 tender-intelligence results with Member 2 bid-readiness checks.

Accepts either a single extraction dictionary, a Member 1 envelope containing
``results``, or a list of extraction dictionaries. Does not fetch external data.
"""
from __future__ import annotations
from typing import Any
from backend.agents.bid_readiness_agent import BidReadinessAgent
from backend.models.company import CompanyProfile

class TenderAssessmentPipeline:
    def __init__(self, readiness_agent: BidReadinessAgent | None = None):
        self.readiness_agent = readiness_agent or BidReadinessAgent()

    @staticmethod
    def _extract_results(payload: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        if isinstance(payload, list):
            return [x for x in payload if isinstance(x, dict)], {}
        if not isinstance(payload, dict):
            raise TypeError("Tender payload must be a dictionary or list of dictionaries.")
        # Member 1 Part 3 envelope.
        if isinstance(payload.get("results"), list):
            return [x for x in payload["results"] if isinstance(x, dict)], {
                "schema_version": payload.get("schema_version"),
                "agent": payload.get("agent"),
                "catalogue_mode": payload.get("catalogue_mode"),
                "limitations": payload.get("limitations", []),
            }
        # Single extraction from the original Member 1 contract.
        if any(k in payload for k in ("normalized_requirements", "eligibility", "documents_required", "tender_id", "id")):
            return [payload], {}
        raise ValueError("No tender extraction found: expected a single extraction or a payload with a results list.")

    def assess(self, company_data: dict[str, Any], tender_payload: Any) -> dict[str, Any]:
        company = CompanyProfile.from_dict(company_data)
        extractions, source_metadata = self._extract_results(tender_payload)
        reports = []
        for extraction in extractions:
            # Member 1's missing-document branch intentionally carries warnings,
            # not fake successful extraction values. Preserve this as review-needed.
            extraction_for_assessment = dict(extraction)
            discovery = extraction.get("discovery") or {}
            tender_id = extraction.get("tender_id") or extraction.get("id") or discovery.get("tender_id")
            if tender_id is not None:
                extraction_for_assessment.setdefault("tender_id", tender_id)
            report = self.readiness_agent.evaluate(company.to_dict(), extraction_for_assessment)
            report["discovery"] = discovery
            report["source_document"] = extraction.get("source_document")
            report["source_metadata"] = extraction.get("source_metadata", {})
            report["cross_checks"] = extraction.get("cross_checks", {})
            warnings = extraction.get("warnings", [])
            if isinstance(warnings, str):
                warnings = [warnings]
            missing_document = bool(extraction.get("source_document") and not extraction.get("normalized_requirements")
                                    and not extraction.get("eligibility") and warnings)
            if warnings or missing_document or report.get("eligibility", {}).get("tender_review_required"):
                report["human_review_required"] = True
                report["source_warnings"] = warnings
                if report.get("overall_status") == "READY_FOR_HUMAN_REVIEW":
                    report["overall_status"] = "REVIEW_REQUIRED_SOURCE_WARNINGS"
                if missing_document:
                    report["action_items"].append({
                        "priority": "HIGH", "type": "SOURCE_DOCUMENT",
                        "item": "Tender source document",
                        "action": "Retrieve and review the official tender document; requirements could not be reliably assessed from this result."
                    })
            # A catalogue/document deadline mismatch should be visible to Member 3.
            cross_check = (report.get("cross_checks") or {}).get("catalogue_vs_document_deadline", {})
            if cross_check.get("status") == "review_required":
                report["action_items"].append({
                    "priority": "HIGH", "type": "DEADLINE_CROSS_CHECK",
                    "item": "Catalogue vs document deadline",
                    "action": "Compare the official tender and latest corrigendum; the catalogue and document deadlines are not confirmed to match."
                })
                report["overall_status"] = "REVIEW_REQUIRED_DEADLINE_CROSS_CHECK"
            reports.append(report)
        reports.sort(key=self._sort_key)
        return {
            "schema_version": "1.0",
            "agent": "member2_tender_assessment_pipeline",
            "company_name": company.company_name,
            "input_tender_count": len(extractions),
            "assessed_tender_count": len(reports),
            "results": reports,
            "source_metadata": source_metadata,
            "limitations": [
                "This pipeline assesses only the tender extractions supplied to it; it does not discover or fetch tenders itself.",
                "Eligibility and document checks are preliminary screening, not legal determinations.",
                "Source evidence, official tender clauses, document authenticity, expiry, and latest corrigenda require human verification.",
            ],
        }

    @staticmethod
    def _sort_key(report: dict[str, Any]) -> tuple[int, float]:
        status_order = {
            "READY_FOR_HUMAN_REVIEW": 0,
            "NOT_READY_OR_INCOMPLETE": 1,
            "REVIEW_REQUIRED": 2,
            "REVIEW_REQUIRED_SOURCE_WARNINGS": 3,
            "REVIEW_REQUIRED_DEADLINE_CROSS_CHECK": 4,
            "REVIEW_REQUIRED_POTENTIAL_ELIGIBILITY_GAPS": 5,
        }
        eligibility = report.get("eligibility") or {}
        score = eligibility.get("eligibility_score")
        return (status_order.get(report.get("overall_status"), 3), -(float(score) if score is not None else -1.0))
