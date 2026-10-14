"""Notification payload builder; delivery is intentionally adapter-based."""
from __future__ import annotations
from typing import Any

class NotificationService:
    def build_change_notifications(self, change_report: dict[str, Any]) -> list[dict[str, Any]]:
        notifications = []
        for change in change_report.get("changes", []):
            severity = str(change.get("severity", "LOW")).upper()
            if severity not in {"HIGH", "MEDIUM"}:
                continue
            notifications.append({
                "event": "TENDER_CHANGE",
                "tender_id": change_report.get("tender_id", "UNKNOWN"),
                "severity": severity,
                "title": f"{severity}: tender field changed — {change.get('field', 'unknown')}",
                "message": f"{change.get('field')} changed from {change.get('previous_value')} to {change.get('current_value')}.",
                "requires_delivery_adapter": True,
            })
        return notifications

    def build_deadline_notification(self, tender_id: str, deadline: str, days_remaining: int) -> dict[str, Any]:
        urgency = "HIGH" if days_remaining <= 2 else ("MEDIUM" if days_remaining <= 7 else "LOW")
        return {
            "event": "DEADLINE_REMINDER", "tender_id": tender_id, "deadline": deadline,
            "days_remaining": days_remaining, "severity": urgency,
            "title": f"Tender deadline in {days_remaining} day(s)",
            "requires_delivery_adapter": True,
            "message": "Verify the official deadline and time zone before relying on this reminder.",
        }
