"""Deterministic quality checks for tender extraction output."""
from __future__ import annotations
from datetime import date
from typing import Any

REQUIRED_FIELDS = ("tender_id", "eligibility", "technical_requirements", "financial_requirements", "documents_required", "deadlines", "normalized_requirements", "evidence")

def _empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}

def assess_tender(tender: dict[str, Any], today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    issues: list[dict[str, str]] = []
    for field in REQUIRED_FIELDS:
        if field not in tender:
            issues.append({"severity": "error", "code": "missing_field", "field": field, "message": f"Required field '{field}' is missing."})
        elif _empty(tender[field]):
            issues.append({"severity": "warning", "code": "empty_field", "field": field, "message": f"Field '{field}' is empty; check the source document."})
    warnings = tender.get("warnings", [])
    if warnings:
        issues.append({"severity": "warning", "code": "extraction_warning", "field": "warnings", "message": f"Source extraction reported {len(warnings)} warning(s)."})
    normalized = tender.get("normalized_requirements") if isinstance(tender.get("normalized_requirements"), dict) else {}
    deadline = normalized.get("bid_submission_deadline_iso")
    if deadline:
        try:
            parsed = date.fromisoformat(str(deadline)[:10])
            if parsed < today:
                issues.append({"severity": "warning", "code": "deadline_passed", "field": "normalized_requirements.bid_submission_deadline_iso", "message": f"Deadline {parsed.isoformat()} is before audit date {today.isoformat()}."})
        except ValueError:
            issues.append({"severity": "error", "code": "invalid_deadline_format", "field": "normalized_requirements.bid_submission_deadline_iso", "message": "Deadline must use ISO date format YYYY-MM-DD."})
    evidence = tender.get("evidence")
    if not isinstance(evidence, dict) or not evidence:
        issues.append({"severity": "warning", "code": "no_evidence_map", "field": "evidence", "message": "Evidence map is missing or empty; verify extracted values manually."})
    cross_checks = tender.get("cross_checks") if isinstance(tender.get("cross_checks"), dict) else {}
    check = cross_checks.get("catalogue_vs_document_deadline")
    if isinstance(check, dict) and check.get("status") == "review_required":
        issues.append({"severity": "warning", "code": "deadline_cross_check", "field": "cross_checks.catalogue_vs_document_deadline", "message": "Catalogue and document deadline need manual comparison."})
    errors = sum(i["severity"] == "error" for i in issues)
    warnings_count = sum(i["severity"] == "warning" for i in issues)
    present = sum(field in tender and not _empty(tender.get(field)) for field in REQUIRED_FIELDS)
    status = "needs_review" if errors or warnings_count or tender.get("review_required", False) else "checks_passed"
    return {"tender_id": tender.get("tender_id"), "quality_status": status, "completeness_score": round(100 * present / len(REQUIRED_FIELDS)), "score_interpretation": "Percentage of required output fields present and non-empty; not confidence or eligibility.", "error_count": errors, "warning_count": warnings_count, "review_required": status != "checks_passed", "issues": issues}

def validate_envelope(payload: Any, today: date | None = None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Input JSON must be an object containing a 'results' array.")
    results = payload.get("results")
    if not isinstance(results, list):
        raise ValueError("Input JSON field 'results' must be an array.")
    if any(not isinstance(item, dict) for item in results):
        raise ValueError("Every item in 'results' must be a JSON object.")
    audits = [assess_tender(item, today=today) for item in results]
    return {"schema_version": "1.0", "agent": "member1_tender_quality_audit", "input_agent": payload.get("agent"), "input_result_count": len(results), "audited_count": len(audits), "needs_review_count": sum(x["review_required"] for x in audits), "error_count": sum(x["error_count"] for x in audits), "warning_count": sum(x["warning_count"] for x in audits), "results": audits, "limitations": ["Deterministic quality audit, not a legal opinion or eligibility decision.", "Completeness is field presence only, not model confidence.", "Verify requirements against the original tender and latest official corrigenda."]}
