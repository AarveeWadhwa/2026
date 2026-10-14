"""Document checklist with conservative matching and evidence-aware inventory support."""
from __future__ import annotations
import re
from typing import Any
from backend.models.company import CompanyProfile

ALIASES = {
    "pan card": {"pan", "pan card", "permanent account number"},
    "gst certificate": {"gst", "gst certificate", "gst registration", "gst registration certificate"},
    "iso certificate": {"iso", "iso certificate", "iso certification"},
    "turnover certificate": {"turnover certificate", "ca turnover certificate", "chartered accountant turnover certificate"},
    "experience certificate": {"experience certificate", "work completion certificate", "completion certificate"},
    "audited financial statements": {"audited financial statements", "audited accounts", "financial statements"},
    "oem authorization": {"oem authorization", "manufacturer authorization", "authorized dealer letter"},
    "emd receipt": {"emd receipt", "earnest money deposit receipt", "emd proof"},
    "technical bid": {"technical bid", "technical proposal"},
    "financial bid": {"financial bid", "price bid", "commercial bid"},
    "company registration certificate": {"company registration certificate", "incorporation certificate", "registration certificate"},
    "udyam certificate": {"udyam certificate", "msme certificate", "udyam registration"},
}

def normalize_document_name(value: str) -> str:
    value = re.sub(r"[_\-]+", " ", str(value).lower())
    value = re.sub(r"\.(pdf|docx?|png|jpe?g|xlsx?)$", "", value)
    return " ".join(re.findall(r"[a-z0-9]+", value))

class ComplianceAgent:
    """Match requested document names to inventory records; never asserts authenticity."""
    def evaluate(self, required_documents: list[str],
                 company: CompanyProfile | dict[str, Any]) -> dict[str, Any]:
        if isinstance(company, CompanyProfile):
            company_profile = company
            available = company.available_documents
        else:
            raw_available = company.get("available_documents", []) if isinstance(company, dict) else []
            # CompanyProfile's public schema historically stores filenames as strings.
            # Preserve richer inventory records here before normalizing the rest of the profile.
            sanitized = dict(company) if isinstance(company, dict) else company
            if isinstance(sanitized, dict):
                sanitized["available_documents"] = [
                    item.get("name", item.get("filename", "")) if isinstance(item, dict) else item
                    for item in raw_available
                ]
            company_profile = CompanyProfile.from_dict(sanitized)
            available = raw_available
        company = company_profile
        records = []
        for item in available:
            if isinstance(item, dict):
                records.append(item)
            else:
                records.append({"name": str(item), "status": "UNVERIFIED"})
        checklist = []
        for required in required_documents or []:
            req_norm = normalize_document_name(required)
            aliases = ALIASES.get(req_norm, {req_norm})
            alias_norm = {normalize_document_name(x) for x in aliases}
            matches = []
            for record in records:
                name = str(record.get("name", record.get("filename", "")))
                norm = normalize_document_name(name)
                if not norm: continue
                # Avoid broad substring matches for short terms. Exact normalized or known alias matches first.
                exact = norm in alias_norm
                alias_contains = any(len(a) >= 8 and (a in norm or norm in a) for a in alias_norm)
                if exact or alias_contains:
                    matches.append({"name": name, "match_type": "EXACT_OR_ALIAS" if exact else "PARTIAL_ALIAS",
                                    "record_status": str(record.get("status", "UNVERIFIED")).upper(),
                                    "expiry_date": record.get("expiry_date"), "source": record.get("source")})
            if not matches:
                status, action = "MISSING", "Obtain or upload this document before bid submission."
            elif any(m["record_status"] == "VALID" for m in matches):
                status, action = "AVAILABLE_MARKED_VALID", "Check the original file, validity, signature, and tender-specific format."
            else:
                status, action = "FOUND_UNVERIFIED", "Verify authenticity, validity, expiry, and tender-specific acceptability."
            checklist.append({"required_document": required, "status": status,
                              "matched_company_documents": matches, "action": action})
        available_count = sum(x["status"] in {"AVAILABLE_MARKED_VALID", "FOUND_UNVERIFIED"} for x in checklist)
        verified_count = sum(x["status"] == "AVAILABLE_MARKED_VALID" for x in checklist)
        total = len(checklist)
        missing_count = sum(x["status"] == "MISSING" for x in checklist)
        return {
            "company_name": company.company_name, "required_document_count": total,
            "available_count": available_count, "verified_count": verified_count,
            "missing_count": missing_count,
            "document_readiness_score": round(available_count / total * 100, 1) if total else None,
            "checklist": checklist,
            "disclaimer": "A filename or inventory status does not independently verify authenticity, expiry, signatures, or tender acceptability.",
        }
