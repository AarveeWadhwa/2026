"""Rule-based replanning policy triggered by material tender snapshot changes."""
from __future__ import annotations
from typing import Any


class ReplanningAgent:
    CRITICAL_FIELDS = {
        "deadline": "Submission deadline changed; refresh schedule and preparation priorities.",
        "emd": "EMD changed; re-check financial readiness and payment arrangements.",
        "documents_required": "Required documents changed; rerun compliance matching and update checklist.",
        "eligibility": "Eligibility conditions changed; rerun eligibility assessment before continuing.",
        "minimum_turnover": "Turnover threshold changed; re-evaluate company financial eligibility.",
        "minimum_experience": "Experience threshold changed; re-evaluate experience eligibility.",
        "certifications": "Certification requirements changed; rerun compliance checks.",
        "technical_requirements": "Technical requirements changed; revisit technical fit and bid recommendation.",
    }

    def plan(self, previous: dict[str, Any] | None, current: dict[str, Any],
             prior_assessment: dict[str, Any] | None = None) -> dict[str, Any]:
        if not previous:
            return {"replan_required": False, "reason": "First observed cycle; baseline memory created.",
                    "changed_fields": [], "steps_to_revisit": ["discovery", "requirement_extraction", "eligibility", "compliance", "bid_analysis", "bid_preparation"],
                    "memory_cycle": "first_seen"}
        changed = [field for field in self.CRITICAL_FIELDS if previous.get(field) != current.get(field)]
        if not changed:
            return {"replan_required": False, "reason": "No material monitored fields changed.",
                    "changed_fields": [], "steps_to_revisit": [], "memory_cycle": "repeat_seen"}
        steps = ["requirement_extraction"]
        if any(f in changed for f in ("eligibility", "minimum_turnover", "minimum_experience")):
            steps.extend(["eligibility", "compliance", "bid_analysis", "bid_preparation"])
        if any(f in changed for f in ("documents_required", "certifications")):
            steps.extend(["compliance", "bid_preparation"])
        if any(f in changed for f in ("deadline", "emd", "technical_requirements")):
            steps.extend(["bid_analysis", "bid_preparation"])
        steps = list(dict.fromkeys(steps))
        explanations = [self.CRITICAL_FIELDS[f] for f in changed]
        return {"replan_required": True, "reason": " ".join(explanations), "changed_fields": sorted(changed),
                "steps_to_revisit": steps, "memory_cycle": "changed_since_previous_cycle",
                "previous_assessment_available": prior_assessment is not None}
