"""Portfolio-level explainable summaries for Member 2 assessment reports."""
from __future__ import annotations
from collections import Counter
from typing import Any

class AssessmentInsights:
    def build(self, assessment: dict[str, Any]) -> dict[str, Any]:
        results = assessment.get("results", [])
        if not isinstance(results, list):
            raise ValueError("assessment.results must be a list")
        statuses: Counter[str] = Counter()
        high_priority = []
        missing_docs = []
        review_tenders = []
        rows = []
        for report in results:
            if not isinstance(report, dict):
                continue
            status = str(report.get("overall_status") or "REVIEW_REQUIRED")
            statuses[status] += 1
            tid = str(report.get("tender_id") or "UNKNOWN")
            discovery = report.get("discovery") or {}
            actions = report.get("action_items") or []
            for action in actions:
                if not isinstance(action, dict):
                    continue
                normalized = {"tender_id": tid, "title": discovery.get("title", tid), **action}
                if str(action.get("priority", "")).upper() == "HIGH":
                    high_priority.append(normalized)
            for item in (report.get("compliance") or {}).get("checklist", []) or []:
                if isinstance(item, dict) and item.get("status") == "MISSING":
                    missing_docs.append({"tender_id": tid, "document": item.get("required_document"), "action": item.get("action")})
            if report.get("human_review_required", True):
                review_tenders.append(tid)
            eligibility = report.get("eligibility") or {}
            compliance = report.get("compliance") or {}
            rows.append({"tender_id": tid, "title": discovery.get("title", tid), "status": status,
                         "eligibility_score": eligibility.get("eligibility_score"),
                         "document_readiness_score": compliance.get("document_readiness_score"),
                         "action_count": len(actions), "human_review_required": bool(report.get("human_review_required", True))})
        rows.sort(key=lambda x: (x["status"] == "READY_FOR_HUMAN_REVIEW", x["eligibility_score"] if x["eligibility_score"] is not None else -1))
        return {"schema_version": "1.0", "agent": "member2_assessment_insights", "tender_count": len(rows),
                "status_counts": dict(statuses), "high_priority_action_count": len(high_priority),
                "high_priority_actions": high_priority, "missing_document_count": len(missing_docs),
                "missing_documents": missing_docs, "human_review_tender_ids": sorted(set(review_tenders)),
                "results": rows, "limitations": ["Summarizes upstream assessment output; it does not independently establish legal eligibility.",
                "Document inventory and status labels do not verify authenticity, expiry, or tender acceptance."]}
