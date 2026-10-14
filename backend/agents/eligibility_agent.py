"""Evidence-aware preliminary eligibility checks."""
from __future__ import annotations
from typing import Any
from backend.models.company import CompanyProfile
from backend.models.tender import TenderRequirements

class EligibilityAgent:
    """Returns PASS, FAIL, or UNKNOWN; unknowns are never silently treated as failures."""
    def evaluate(self, company: CompanyProfile | dict[str, Any],
                 tender: TenderRequirements | dict[str, Any]) -> dict[str, Any]:
        company = company if isinstance(company, CompanyProfile) else CompanyProfile.from_dict(company)
        if isinstance(tender, dict):
            tender = TenderRequirements.from_extraction(tender)
        checks = [
            self._numeric_check("annual_turnover", "Annual turnover", company.annual_turnover_inr,
                                tender.minimum_turnover_inr, "INR", tender.evidence.get("minimum_turnover")),
            self._numeric_check("experience", "Relevant experience", company.years_experience,
                                tender.minimum_experience_years, "years", tender.evidence.get("minimum_experience")),
            self._location_check(company.location, tender.location_requirement,
                                 tender.evidence.get("location_requirement")),
        ]
        company_certs = [self._norm(x) for x in company.certifications]
        for required in tender.certifications:
            req = self._norm(required)
            present = any(req == c or req in c for c in company_certs)
            status = "PASS" if present else ("UNKNOWN" if not company.certifications else "FAIL")
            checks.append({
                "key": f"certification:{required}", "requirement": f"Certification: {required}",
                "status": status, "company_value": company.certifications, "required_value": required,
                "evidence": tender.evidence.get(f"certification:{required}") or tender.evidence.get("certifications"),
                "explanation": f"Matching certification listed: {required}." if present else
                    (f"Company certification inventory is empty; verify {required}." if not company.certifications
                     else f"No matching certification for {required} is listed."),
            })
        definite = [c for c in checks if c["status"] in {"PASS", "FAIL"}]
        passed = sum(c["status"] == "PASS" for c in definite)
        failed = [c for c in checks if c["status"] == "FAIL"]
        unknown = [c for c in checks if c["status"] == "UNKNOWN"]
        outcome = "POTENTIAL_GAPS" if failed else ("NEEDS_REVIEW" if unknown or tender.review_required else "MEETS_CHECKED_CRITERIA")
        return {
            "company_name": company.company_name, "tender_id": tender.tender_id,
            "outcome": outcome,
            "eligibility_score": round(passed / len(definite) * 100, 1) if definite else None,
            "checks": checks, "failed_checks": failed, "unknown_checks": unknown,
            "tender_review_required": tender.review_required,
            "tender_review_reasons": tender.review_reasons,
            "financial_obligations": {"emd_inr": tender.emd_inr, "tender_fee_inr": tender.tender_fee_inr,
                                      "deadline": tender.deadline},
            "disclaimer": "Preliminary screening only. Confirm each condition against the original tender and supporting records.",
        }

    @staticmethod
    def _norm(value: str | None) -> str:
        return " ".join((value or "").lower().replace("-", " ").split())

    def _numeric_check(self, key, label, actual, required, unit, evidence=None):
        if required is None: status, explanation = "UNKNOWN", "No reliable normalized threshold was found."
        elif actual is None: status, explanation = "UNKNOWN", "The company profile does not contain this value."
        elif actual >= required: status, explanation = "PASS", f"Company value meets or exceeds the required {unit} threshold."
        else: status, explanation = "FAIL", f"Company value is below the required {unit} threshold."
        return {"key": key, "requirement": label, "status": status, "company_value": actual,
                "required_value": required, "unit": unit, "evidence": evidence, "explanation": explanation}

    def _location_check(self, actual, required, evidence=None):
        if not required: status, explanation = "UNKNOWN", "No clear location restriction was extracted."
        elif not actual: status, explanation = "UNKNOWN", "Company location is not provided."
        elif self._norm(required) in self._norm(actual) or self._norm(actual) in self._norm(required):
            status, explanation = "PASS", "Company location appears consistent with the tender location."
        else: status, explanation = "UNKNOWN", "Location wording differs; confirm the precise legal or delivery restriction."
        return {"key": "location", "requirement": "Location", "status": status,
                "company_value": actual, "required_value": required, "evidence": evidence,
                "explanation": explanation}
