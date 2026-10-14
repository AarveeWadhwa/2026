"""Combine eligibility and document compliance into a transparent readiness report."""
from __future__ import annotations
from typing import Any
from backend.agents.eligibility_agent import EligibilityAgent
from backend.agents.compliance_agent import ComplianceAgent
from backend.models.tender import TenderRequirements

class BidReadinessAgent:
    def __init__(self):
        self.eligibility_agent = EligibilityAgent()
        self.compliance_agent = ComplianceAgent()

    def evaluate(self, company: dict[str, Any], extraction: dict[str, Any]) -> dict[str, Any]:
        tender = TenderRequirements.from_extraction(extraction)
        eligibility = self.eligibility_agent.evaluate(company, tender)
        compliance = self.compliance_agent.evaluate(tender.documents_required, company)
        if eligibility["outcome"] == "POTENTIAL_GAPS":
            status = "REVIEW_REQUIRED_POTENTIAL_ELIGIBILITY_GAPS"
        elif eligibility["outcome"] == "NEEDS_REVIEW" or compliance["missing_count"] > 0:
            status = "NOT_READY_OR_INCOMPLETE"
        elif compliance["document_readiness_score"] is None:
            status = "REVIEW_REQUIRED"
        else:
            status = "READY_FOR_HUMAN_REVIEW"
        actions = []
        for check in eligibility["checks"]:
            if check["status"] in {"FAIL", "UNKNOWN"}:
                actions.append({"priority": "HIGH" if check["status"] == "FAIL" else "MEDIUM",
                                "type": "ELIGIBILITY", "item": check["requirement"],
                                "action": check["explanation"]})
        for item in compliance["checklist"]:
            if item["status"] == "MISSING":
                actions.append({"priority": "HIGH", "type": "DOCUMENT",
                                "item": item["required_document"], "action": item["action"]})
            elif item["status"] == "FOUND_UNVERIFIED":
                actions.append({"priority": "MEDIUM", "type": "DOCUMENT",
                                "item": item["required_document"], "action": item["action"]})
        if tender.review_required:
            actions.append({"priority": "HIGH", "type": "SOURCE_REVIEW", "item": "Tender extraction",
                            "action": "Review extraction warnings and verify extracted requirements against the source document."})
        return {
            "tender_id": tender.tender_id, "company_name": eligibility["company_name"],
            "overall_status": status, "eligibility": eligibility, "compliance": compliance,
            "action_items": actions,
            "human_review_required": True,
            "disclaimer": "Decision support only; not a legal determination or a guarantee of tender eligibility.",
        }
