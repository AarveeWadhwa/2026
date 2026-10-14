"""Evidence-backed tender requirement extraction for BidPilot AI.

This is a transparent, rule-based baseline (not an LLM). It emits readable
fields for the existing team contract and normalized candidate values for
Member 2's eligibility/compliance agents. Human verification is mandatory.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.services.document_parser import extract_document

MONEY = r"(?:₹\s*|INR\s*|Rs\.?\s*)?[\d,]+(?:\.\d+)?\s*(?:crore|crores|cr|lakh|lakhs|lac|lacs|million)?"


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"\s+", " ", value).strip(" .,:;\t\n-") or None


def _first(patterns: list[str], text: str) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            return _clean(match.group(1))
    return None


def _snippets(text: str, patterns: list[str], radius: int = 120, limit: int = 3) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE | re.MULTILINE):
            start = max(0, match.start() - radius)
            end = min(len(text), match.end() + radius)
            snippet = re.sub(r"\s+", " ", text[start:end]).strip()
            if snippet and snippet not in seen:
                seen.add(snippet)
                results.append(snippet)
                if len(results) >= limit:
                    return results
    return results


def _money_inr(value: str | None) -> int | None:
    """Convert common Indian tender amounts into whole INR; unknown formats return None."""
    if not value:
        return None
    match = re.search(r"([\d,]+(?:\.\d+)?)\s*(crores?|cr|lakhs?|lacs?|lac|million)?", value, re.I)
    if not match:
        return None
    try:
        amount = float(match.group(1).replace(",", ""))
    except ValueError:
        return None
    unit = (match.group(2) or "").lower()
    multiplier = 1
    if unit in {"crore", "crores", "cr"}:
        multiplier = 10_000_000
    elif unit in {"lakh", "lakhs", "lac", "lacs"}:
        multiplier = 100_000
    elif unit == "million":
        multiplier = 1_000_000
    return int(round(amount * multiplier))


def _date_iso(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", value.strip(), flags=re.I)
    formats = (
        "%d-%b-%Y", "%d-%B-%Y", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
        "%Y-%m-%d", "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y",
        "%d-%b-%y", "%d/%m/%y", "%d-%m-%y",
    )
    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _experience_months(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"(\d+)\s*(years?|months?)", value, re.I)
    if not match:
        return None
    number = int(match.group(1))
    return number * 12 if match.group(2).lower().startswith("year") else number


class TenderRequirementAgent:
    """Extract common requirements and retain evidence for review."""

    def extract(self, text: str, tender_id: str | None = None,
                source_file: str | None = None, document_warnings: list[str] | None = None) -> dict[str, Any]:
        if not text or not text.strip():
            raise ValueError("Tender text is empty.")

        turnover = _first([
            rf"(?:minimum|required)\s+(?:average\s+)?(?:annual\s+)?turnover\s*(?:of|:|is)?\s*({MONEY})",
            rf"turnover.{{0,70}}?({MONEY})",
        ], text)
        experience = _first([
            r"(?:minimum|required)\s+(?:relevant\s+|work\s+)?experience\s*(?:of|:|is)?\s*(\d+\s*(?:years?|months?))",
            r"(\d+\s*(?:years?|months?))\s+(?:of\s+)?(?:relevant\s+)?experience",
        ], text)
        deadline = _first([
            r"(?:bid\s+submission\s+)?(?:last\s+date(?:\s+for\s+submission)?|deadline|due\s+date|closing\s+date)\s*[:\-]?\s*((?:\d{4}-\d{1,2}-\d{1,2})|(?:\d{1,2}[-/. ](?:\d{1,2}|[A-Za-z]{3,9})[-/. ,]*\d{2,4})|(?:\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4}))",
        ], text)
        emd = _first([
            rf"(?:earnest\s+money\s+deposit|\bEMD\b)\s*\)?\s*(?:amount)?\s*(?:of|:|is)?\s*({MONEY})",
        ], text)
        tender_fee = _first([
            rf"(?:tender\s+(?:document\s+)?fee|document\s+fee)\s*(?:of|:|is)?\s*({MONEY})",
        ], text)
        location = _first([
            r"(?:delivery|work|service)\s+location\s*[:\-]\s*([^\n.;]{2,100})",
            r"(?:only\s+for|within)\s+([A-Z][A-Za-z ,]{2,60})\s+(?:based|registered|located)\s+(?:companies|bidders|firms)",
            r"^Location\s*:\s*([^\n]+)",
        ], text)

        cert_pattern = r"\b(?:ISO\s*[- ]?\s*\d{3,5}(?:\s*:\s*\d{4})?|BIS|CMMI(?:\s+Level\s+[0-5])?|MSME|Udyam|GST(?:\s+registration)?|PAN|OEM authorization|Startup India)\b"
        certifications = sorted({re.sub(r"\s+", " ", item).strip().upper() for item in re.findall(cert_pattern, text, re.I)})

        doc_patterns = {
            "PAN card": r"\bPAN\s*(?:card|copy|details)?\b",
            "GST certificate": r"\bGST\s*(?:certificate|registration|registration certificate)\b",
            "Audited financial statements": r"\b(?:audited\s+)?financial statements\b|\baudit report\b",
            "Turnover certificate": r"\b(?:CA[- ]?certified\s+)?turnover certificate\b|\bcertificate of turnover\b",
            "Experience certificate": r"\bexperience certificate\b|\bwork completion certificate\b|\bproof of experience\b",
            "ISO certificate": r"\bISO\s*[- ]?\s*\d{3,5}(?:\s*:\s*\d{4})?\s+certificate\b|\bISO certificate\b",
            "OEM authorization": r"\bOEM authorization(?: letter)?\b|\bmanufacturer authorization\b",
            "EMD receipt": r"\bEMD receipt\b|\bproof of EMD\b",
            "Technical bid": r"\btechnical bid\b|\btechnical proposal\b",
            "Financial bid": r"\bfinancial bid\b|\bprice bid\b|\bcommercial bid\b",
            "Company registration certificate": r"\bcompany registration certificate\b|\bcertificate of incorporation\b",
            "Udyam certificate": r"\bUdyam certificate\b|\bMSME certificate\b",
            "Technical methodology": r"\btechnical methodology\b|\bmethodology statement\b",
            "Service delivery plan": r"\bservice delivery plan\b|\bdelivery plan\b",
        }
        documents = [label for label, pattern in doc_patterns.items() if re.search(pattern, text, re.I)]

        technical: list[str] = []
        for line in text.splitlines():
            cleaned = re.sub(r"\s+", " ", line).strip(" •-\t")
            if cleaned and re.search(r"\b(specification|technical|capacity|warranty|delivery|compatible|standard|quantity|RAM|SSD|response.time|cybersecurity|vulnerability|installation|support)\b", cleaned, re.I):
                if cleaned not in technical:
                    technical.append(cleaned[:400])

        criteria = _first([
            r"(?:evaluation criteria|evaluation method|evaluation process)\s*[:\-]?\s*([^\n.]{5,250})",
        ], text)
        other_conditions = []
        for line in text.splitlines():
            cleaned = re.sub(r"\s+", " ", line).strip(" •-\t")
            if re.search(r"\b(must|shall|required|should)\b", cleaned, re.I) and re.search(r"\b(GST|PAN|registered|certification|certified|bidder|manufacturer|blacklist|blacklisted|joint venture|consortium|solvency)\b", cleaned, re.I):
                if cleaned not in other_conditions and cleaned not in technical:
                    other_conditions.append(cleaned[:400])

        evidence_patterns = {
            "minimum_turnover": [r"turnover"],
            "minimum_experience": [r"experience"],
            "location_requirement": [r"(?:delivery|work|service)\s+location", r"^Location"],
            "bid_submission_deadline": [r"(?:last\s+date|deadline|due\s+date|closing\s+date)"],
            "emd": [r"earnest\s+money\s+deposit", r"\bEMD\b"],
            "tender_fee": [r"tender\s+(?:document\s+)?fee", r"document\s+fee"],
            "certifications": [r"ISO", r"certification", r"GST"],
            "documents_required": [r"documents required", r"PAN", r"certificate", r"technical bid", r"financial bid"],
            "technical_requirements": [r"technical", r"specification", r"warranty", r"quantity"],
            "evaluation_criteria": [r"evaluation criteria", r"evaluation method", r"evaluation process"],
        }
        evidence = {key: found for key, patterns in evidence_patterns.items() if (found := _snippets(text, patterns))}

        warnings = list(document_warnings or [])
        warnings.extend([
            "Rule-based extraction is a screening aid and may miss tables, footnotes, exceptions, or requirements expressed indirectly.",
            "Verify every extracted requirement against the original tender, annexures, and latest corrigenda before bidding.",
        ])
        for field, value in [("minimum turnover", turnover), ("minimum experience", experience), ("bid submission deadline", deadline)]:
            if not value:
                warnings.append(f"No clear {field} was detected; check the document manually.")
        if deadline and not _date_iso(deadline):
            warnings.append(f"Deadline '{deadline}' was detected but could not be normalized to ISO date; verify the format.")
        if not evidence:
            warnings.append("No evidence snippets were captured; manually inspect the source document.")

        financial = []
        if emd:
            financial.append({"type": "EMD", "value": emd})
        if tender_fee:
            financial.append({"type": "Tender fee", "value": tender_fee})

        return {
            "schema_version": "1.1",
            "tender_id": tender_id,
            "source_document": source_file,
            "eligibility": {
                "minimum_turnover": turnover,
                "minimum_experience": experience,
                "location_requirement": location,
                "other_conditions": other_conditions,
            },
            "technical_requirements": technical,
            "financial_requirements": financial,
            "certifications": certifications,
            "documents_required": documents,
            "deadlines": {"bid_submission_deadline": deadline},
            "evaluation_criteria": criteria,
            "normalized_requirements": {
                "minimum_annual_turnover_inr": _money_inr(turnover),
                "minimum_experience_months": _experience_months(experience),
                "location_requirement": location,
                "emd_inr": _money_inr(emd),
                "tender_fee_inr": _money_inr(tender_fee),
                "bid_submission_deadline_iso": _date_iso(deadline),
                "certifications": certifications,
                "documents_required": documents,
            },
            "evidence": evidence,
            "warnings": list(dict.fromkeys(warnings)),
            "review_required": True,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract structured requirements from a tender document.")
    parser.add_argument("document", help="Path to a .txt, .md, .pdf, or .docx tender document")
    parser.add_argument("--tender-id", help="Override the tender ID inferred from the filename")
    parser.add_argument("--output", help="Optional path to save the JSON result")
    args = parser.parse_args()

    path = Path(args.document)
    document = extract_document(path)
    tender_id = args.tender_id or path.stem
    result = TenderRequirementAgent().extract(
        document.text, tender_id=tender_id, source_file=document.source_file,
        document_warnings=document.warnings,
    )
    result["source_metadata"] = {
        "file_type": document.file_type,
        "page_count": document.page_count,
        "character_count": document.character_count,
        "sha256": document.sha256,
    }
    rendered = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
        print(f"Saved extracted requirements to {output_path}")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
