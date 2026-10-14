"""Transparent bid analysis that preserves the original Member 3 API."""
from __future__ import annotations
from typing import Any

class BidAnalysisAgent:
    def analyze(self, eligibility_result: dict[str, Any], compliance_result: dict[str, Any],
                tender: dict[str, Any] | None = None,
                change_report: dict[str, Any] | None = None) -> dict[str, Any]:
        tender = tender or {}
        strengths, risks, actions, evidence = [], [], [], []
        for check in eligibility_result.get("checks", []) or []:
            status = str(check.get("status", "UNKNOWN")).upper()
            label = str(check.get("requirement", check.get("key", "Requirement")))
            if status == "PASS": strengths.append(f"{label} passed.")
            elif status == "FAIL":
                risks.append(f"Potential eligibility gap: {label}.")
                actions.append({"priority": "HIGH", "action": check.get("explanation", f"Review {label}.")})
            else:
                risks.append(f"Unverified criterion: {label}.")
                actions.append({"priority": "MEDIUM", "action": check.get("explanation", f"Verify {label}.")})
            if check.get("evidence"):
                evidence.append({"type": "eligibility", "field": label, "source_evidence": check["evidence"]})
        failed = eligibility_result.get("failed_checks", []) or []
        unknown = eligibility_result.get("unknown_checks", []) or []
        missing_docs = [x.get("required_document", "Unnamed document")
                        for x in compliance_result.get("checklist", []) or [] if x.get("status") == "MISSING"]
        for item in compliance_result.get("checklist", []) or []:
            label = str(item.get("required_document", "Required document"))
            status = str(item.get("status", "MISSING")).upper()
            if status == "MISSING":
                risks.append(f"Required document missing: {label}")
                actions.append({"priority": "HIGH", "action": item.get("action", f"Obtain {label}.")})
            elif status not in {"AVAILABLE_MARKED_VALID", "AVAILABLE"}:
                risks.append(f"Document needs verification: {label}")
                actions.append({"priority": "MEDIUM", "action": item.get("action", f"Verify {label}.")})
            else:
                strengths.append(f"Document inventory lists: {label}.")
        if change_report:
            for change in change_report.get("changes", []):
                sev = str(change.get("severity", "LOW")).upper()
                if sev in {"HIGH", "MEDIUM"}:
                    risks.append(f"Tender field '{change.get('field')}' changed.")
                    actions.append({"priority": sev, "action": "Review the changed tender clause and update the bid checklist."})
        score = eligibility_result.get("eligibility_score")
        doc_score = compliance_result.get("document_readiness_score")
        components = []
        if score is not None: components.append((float(score), .65))
        if doc_score is not None: components.append((float(doc_score), .35))
        overall = round(sum(s*w for s,w in components) / sum(w for _,w in components), 1) if components else None
        if failed or missing_docs: recommendation = "ACTION_REQUIRED"
        elif unknown: recommendation = "NEEDS_HUMAN_REVIEW"
        elif overall is not None and overall >= 80: recommendation = "STRONG_CANDIDATE"
        elif overall is not None: recommendation = "REVIEW_BEFORE_BIDDING"
        else: recommendation = "INSUFFICIENT_DATA"
        readiness = ("POTENTIAL_ELIGIBILITY_GAPS" if failed else
                     "NOT_READY_OR_REVIEW_REQUIRED" if missing_docs or unknown else
                     "REVIEW_CHANGES_BEFORE_SUBMISSION" if change_report and change_report.get("high_priority_count", 0) else
                     "READY_FOR_HUMAN_REVIEW")
        return {
            "tender_id": tender.get("tender_id") or eligibility_result.get("tender_id"),
            "tender_title": tender.get("title", "Untitled tender"),
            "company_name": eligibility_result.get("company_name") or compliance_result.get("company_name", "Company"),
            "eligibility_score": score, "document_readiness_score": doc_score, "overall_score": overall,
            "recommendation": recommendation, "readiness_status": readiness,
            "strengths": strengths, "risks": risks, "action_items": actions,
            "missing_documents": missing_docs, "unknown_eligibility_checks": unknown,
            "deadline": tender.get("deadline"), "evidence": evidence,
            "human_review_required": True,
            "assumptions": ["Analysis is based only on supplied reports and snapshots.",
                "Document inventory status does not establish authenticity or tender acceptance.",
                "A human reviewer must validate the original tender and all applicable corrigenda."],
            "score_note": "Weighted readiness indicator, not a probability of winning or a legal eligibility determination.",
        }
