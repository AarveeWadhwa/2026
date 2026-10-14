"""Structured reports shared by Member 3 agents; preserves the original report API."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any

@dataclass
class BidReadinessReport:
    tender_id: str
    tender_title: str
    company_name: str
    recommendation: str
    overall_score: float | None
    eligibility_score: float | None
    document_readiness_score: float | None
    deadline: str | None = None
    strengths: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    human_review_required: bool = True
    disclaimer: str = (
        "This report is preliminary decision support. Verify source tender documents, "
        "corrigenda, eligibility clauses, and all evidence before submitting a bid."
    )
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class ChangeEvent:
    tender_id: str
    change_type: str
    field: str
    previous_value: Any = None
    current_value: Any = None
    severity: str = "MEDIUM"
    evidence: dict[str, Any] = field(default_factory=dict)
    detected_at: str | None = None
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class BidAnalysisReport:
    tender_id: str
    readiness_status: str
    strengths: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    action_items: list[dict[str, Any]] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
