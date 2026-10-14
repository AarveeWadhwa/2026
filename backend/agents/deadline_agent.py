"""Deadline/corrigendum monitoring via explicit snapshot comparison."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from backend.models.report import ChangeEvent

DATE_FORMATS = (
    "%Y-%m-%d", "%d-%b-%Y", "%d-%B-%Y", "%d/%m/%Y", "%d-%m-%Y",
    "%d %b %Y", "%d %B %Y", "%m/%d/%Y",
)
def normalize_date(value: str | None) -> str | None:
    if not value: return None
    value = str(value).strip()
    for fmt in DATE_FORMATS:
        try: return datetime.strptime(value, fmt).date().isoformat()
        except ValueError: continue
    return None

IMPORTANT_FIELDS = {
    "deadline": "HIGH", "submission_deadline": "HIGH", "emd": "HIGH", "emd_inr": "HIGH",
    "tender_fee": "MEDIUM", "tender_fee_inr": "MEDIUM", "eligibility": "HIGH",
    "eligibility_criteria": "HIGH", "documents_required": "HIGH", "required_documents": "HIGH",
    "technical_requirements": "HIGH", "corrigendum": "HIGH", "corrigendum_id": "HIGH",
    "status": "HIGH", "estimated_value": "MEDIUM",
}
def _stable(value: Any) -> str:
    if isinstance(value, dict):
        return "{" + ",".join(f"{k}:{_stable(value[k])}" for k in sorted(value)) + "}"
    if isinstance(value, (list, tuple)): return "[" + ",".join(_stable(x) for x in value) + "]"
    return str(value).strip() if value is not None else ""

class DeadlineCorrigendumAgent:
    TRACKED_FIELDS = {
        "deadline": "Bid submission deadline", "estimated_value": "Estimated tender value",
        "title": "Tender title", "status": "Tender status",
        "corrigendum_id": "Corrigendum reference", "source_url": "Tender source URL",
    }
    def compare(self, previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
        changes = []
        for field, label in self.TRACKED_FIELDS.items():
            old, new = previous.get(field), current.get(field)
            if field == "deadline":
                old_n, new_n = normalize_date(old), normalize_date(new)
                changed = old_n != new_n and (old_n is not None or new_n is not None)
            else:
                changed = old != new and (old is not None or new is not None)
            if changed:
                changes.append({"field": field, "label": label, "old_value": old,
                    "new_value": new, "message": f"{label} changed from {old or 'not listed'} to {new or 'not listed'}."})
        return {"tender_id": current.get("tender_id") or previous.get("tender_id"),
            "has_changes": bool(changes), "changes": changes,
            "alert_messages": [x["message"] for x in changes],
            "human_review_required": bool(changes)}

    def compare_snapshots(self, previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(previous, dict) or not isinstance(current, dict):
            raise TypeError("Previous and current snapshots must be dictionaries.")
        tender_id = str(current.get("tender_id") or current.get("id") or previous.get("tender_id") or previous.get("id") or "UNKNOWN")
        changes = []
        for key in dict.fromkeys([*previous.keys(), *current.keys()]):
            before, after = previous.get(key), current.get(key)
            if _stable(before) == _stable(after): continue
            changes.append(ChangeEvent(tender_id=tender_id,
                change_type="ADDED" if key not in previous else ("REMOVED" if key not in current else "MODIFIED"),
                field=key, previous_value=before, current_value=after,
                severity=IMPORTANT_FIELDS.get(key, "LOW"),
                evidence={"previous_snapshot_field": key, "current_snapshot_field": key},
                detected_at=datetime.now(timezone.utc).isoformat()).to_dict())
        return {"tender_id": tender_id, "change_count": len(changes),
            "high_priority_count": sum(x["severity"] == "HIGH" for x in changes),
            "changes": changes, "monitoring_mode": "SNAPSHOT_COMPARISON",
            "disclaimer": "Compares supplied snapshots only; does not monitor a portal."}

# Alias keeps imports used by existing files working.
DeadlineAgent = DeadlineCorrigendumAgent
