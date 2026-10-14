"""Normalized tender requirements model with backward-compatible extraction adapters."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any
import re

@dataclass
class TenderRequirements:
    tender_id: str | None = None
    minimum_turnover_inr: float | None = None
    minimum_experience_years: float | None = None
    location_requirement: str | None = None
    certifications: list[str] = field(default_factory=list)
    documents_required: list[str] = field(default_factory=list)
    other_conditions: list[str] = field(default_factory=list)
    emd_inr: float | None = None
    tender_fee_inr: float | None = None
    deadline: str | None = None
    technical_requirements: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    review_required: bool = False
    review_reasons: list[str] = field(default_factory=list)

    @classmethod
    def from_extraction(cls, extraction: dict[str, Any]) -> "TenderRequirements":
        """Accept both the original Member 1 extraction and Part 2 normalized output."""
        if not isinstance(extraction, dict):
            raise TypeError("Tender extraction must be a dictionary.")
        normalized = extraction.get("normalized_requirements") or {}
        eligibility = extraction.get("eligibility") or {}
        raw = {**extraction, **normalized}
        def first(*values):
            return next((v for v in values if v is not None and v != ""), None)
        turnover = first(raw.get("minimum_turnover_inr"), eligibility.get("minimum_turnover"),
                         raw.get("minimum_turnover"), raw.get("turnover_requirement"))
        experience = first(raw.get("minimum_experience_years"), eligibility.get("minimum_experience"),
                           raw.get("minimum_experience"), raw.get("experience_requirement"))
        location = first(raw.get("location_requirement"), eligibility.get("location_requirement"))
        certs = first(raw.get("certifications"), eligibility.get("certifications")) or []
        docs = first(raw.get("documents_required"), raw.get("required_documents"),
                     raw.get("documents"), eligibility.get("documents_required")) or []
        conditions = first(raw.get("other_conditions"), eligibility.get("other_conditions")) or []
        technical = first(raw.get("technical_requirements"), raw.get("technical_conditions")) or []
        evidence = raw.get("evidence") or raw.get("field_evidence") or {}
        warnings = raw.get("warnings") or raw.get("review_reasons") or []
        return cls(
            tender_id=raw.get("tender_id") or raw.get("id"),
            minimum_turnover_inr=parse_money_inr(turnover),
            minimum_experience_years=parse_years(experience),
            location_requirement=str(location).strip() if location else None,
            certifications=_as_list(certs),
            documents_required=_as_list(docs),
            other_conditions=_as_list(conditions),
            emd_inr=parse_money_inr(first(raw.get("emd_inr"), raw.get("emd"), raw.get("emd_amount"))),
            tender_fee_inr=parse_money_inr(first(raw.get("tender_fee_inr"), raw.get("tender_fee"), raw.get("fee"))),
            deadline=str(first(raw.get("deadline"), raw.get("submission_deadline")) or "") or None,
            technical_requirements=_as_list(technical),
            evidence=evidence if isinstance(evidence, dict) else {},
            review_required=bool(raw.get("review_required", False) or warnings),
            review_reasons=_as_list(warnings),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

def _as_list(value: Any) -> list[str]:
    if value is None: return []
    if isinstance(value, str): return [value.strip()] if value.strip() else []
    if isinstance(value, (list, tuple, set)): return [str(x).strip() for x in value if str(x).strip()]
    return []

def parse_money_inr(value: Any) -> float | None:
    if value is None or value == "": return None
    if isinstance(value, (int, float)): return float(value)
    text = str(value).lower().replace(",", "").replace("₹", "").replace("inr", "").strip()
    match = re.search(r"(\d+(?:\.\d+)?)\s*(crore|crores|cr|lakh|lakhs|lac|lacs|million)?", text)
    if not match: return None
    amount = float(match.group(1))
    unit = match.group(2) or ""
    if unit in {"crore", "crores", "cr"}: amount *= 10_000_000
    elif unit in {"lakh", "lakhs", "lac", "lacs"}: amount *= 100_000
    elif unit == "million": amount *= 1_000_000
    return amount

def parse_years(value: Any) -> float | None:
    if value is None or value == "": return None
    if isinstance(value, (int, float)): return float(value)
    match = re.search(r"(\d+(?:\.\d+)?)\s*(year|years|yr|yrs|month|months)", str(value).lower())
    if not match: return None
    number = float(match.group(1))
    return number / 12 if match.group(2).startswith("month") else number
