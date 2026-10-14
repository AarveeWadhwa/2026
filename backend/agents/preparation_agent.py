"""Generate a practical, human-reviewable bid preparation checklist."""
from __future__ import annotations
from typing import Any

class PreparationAgent:
    DEFAULT_STEPS = [
        ("Confirm tender version and all corrigenda", "HIGH"),
        ("Verify eligibility claims against company records", "HIGH"),
        ("Check document authenticity, signatures, expiry, and file format", "HIGH"),
        ("Confirm EMD, tender fee, exemptions, and payment proof", "HIGH"),
        ("Validate technical and financial bid separation", "HIGH"),
        ("Review submission portal instructions and file-size limits", "MEDIUM"),
        ("Assign final review and approval owner", "MEDIUM"),
        ("Submit before the verified deadline and retain receipt", "HIGH"),
    ]

    def prepare(self, tender_id: str, bid_analysis: dict[str, Any],
                compliance_report: dict[str, Any] | None = None,
                deadline: str | None = None) -> dict[str, Any]:
        items = []
        for index, (label, priority) in enumerate(self.DEFAULT_STEPS, 1):
            items.append({"id": f"GEN-{index:02d}", "task": label, "priority": priority,
                          "status": "PENDING", "source": "GENERAL_BID_CONTROL"})
        for action in bid_analysis.get("action_items", []):
            items.append({"id": f"RISK-{len(items)+1:02d}",
                          "task": action.get("action", "Review identified bid risk"),
                          "priority": action.get("priority", "MEDIUM"), "status": "PENDING",
                          "source": "BID_ANALYSIS"})
        if compliance_report:
            for doc in compliance_report.get("checklist", []):
                if doc.get("status") == "MISSING":
                    items.append({"id": f"DOC-{len(items)+1:02d}",
                                  "task": f"Obtain and verify: {doc.get('required_document', 'required document')}",
                                  "priority": "HIGH", "status": "PENDING", "source": "COMPLIANCE"})
        return {
            "tender_id": tender_id, "deadline": deadline,
            "task_count": len(items), "items": items,
            "completion_note": "Tasks are pending until explicitly checked by the bid team.",
            "human_review_required": True,
            "disclaimer": "This checklist supports human preparation and does not submit a bid automatically.",
        }


class BidPreparationAgent(PreparationAgent):
    """Backward-compatible adapter for the original Member 3 API."""
    def prepare(self, analysis, tender=None, compliance_result=None):
        tender = tender or {}
        result = super().prepare(
            str(analysis.get("tender_id") or tender.get("tender_id") or "UNKNOWN"),
            analysis, compliance_result, analysis.get("deadline") or tender.get("deadline"))
        result.update({
            "tender_title": analysis.get("tender_title") or tender.get("title") or "Untitled tender",
            "company_name": analysis.get("company_name") or "Company",
            "recommendation": analysis.get("recommendation") or "INSUFFICIENT_DATA",
            "overall_score": analysis.get("overall_score"),
            "eligibility_score": analysis.get("eligibility_score"),
            "document_readiness_score": analysis.get("document_readiness_score"),
            "strengths": analysis.get("strengths", []),
            "risks": analysis.get("risks", []),
            "missing_documents": analysis.get("missing_documents", []),
            "actions": [x["task"] for x in result.get("items", [])],
            "corrigendum_review_required": True,
        })
        return result
