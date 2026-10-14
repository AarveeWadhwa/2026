"""Orchestrate Member 3 analysis, snapshot comparison, checklist and alert payloads.

This pipeline consumes JSON already produced by upstream agents. It does not scrape
portals, send notifications, or make a legal eligibility determination.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from backend.agents.bid_analysis_agent import BidAnalysisAgent
from backend.agents.deadline_agent import DeadlineCorrigendumAgent
from backend.agents.preparation_agent import PreparationAgent
from backend.services.notification_service import NotificationService


class BidWorkspacePipeline:
    def __init__(self) -> None:
        self.analysis_agent = BidAnalysisAgent()
        self.change_agent = DeadlineCorrigendumAgent()
        self.preparation_agent = PreparationAgent()
        self.notifications = NotificationService()

    @staticmethod
    def _index_by_tender_id(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        indexed: dict[str, dict[str, Any]] = {}
        for record in records:
            tid = str(record.get("tender_id") or record.get("id") or "").strip()
            if not tid:
                raise ValueError("Every tender snapshot must include tender_id or id.")
            indexed[tid] = record
        return indexed

    def run(self, assessments: list[dict[str, Any]],
            current_snapshots: list[dict[str, Any]] | None = None,
            previous_snapshots: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        current_by_id = self._index_by_tender_id(current_snapshots or [])
        previous_by_id = self._index_by_tender_id(previous_snapshots or [])
        results = []
        all_notifications: list[dict[str, Any]] = []
        for assessment in assessments:
            tid = str(assessment.get("tender_id") or assessment.get("id") or "").strip()
            if not tid:
                raise ValueError("Every assessment must include tender_id or id.")
            eligibility = assessment.get("eligibility_result") or {}
            compliance = assessment.get("compliance_result") or {}
            tender = assessment.get("tender") or current_by_id.get(tid) or {"tender_id": tid}
            change_report = None
            if tid in current_by_id and tid in previous_by_id:
                change_report = self.change_agent.compare_snapshots(previous_by_id[tid], current_by_id[tid])
            analysis = self.analysis_agent.analyze(eligibility, compliance, tender, change_report)
            analysis["tender_id"] = tid
            checklist = self.preparation_agent.prepare(tid, analysis, compliance, tender.get("deadline"))
            tender_notifications = self.notifications.build_change_notifications(change_report or {})
            for notice in tender_notifications:
                notice["tender_id"] = tid
            all_notifications.extend(tender_notifications)
            results.append({
                "tender_id": tid,
                "analysis": analysis,
                "change_report": change_report,
                "preparation_checklist": checklist,
                "notifications": tender_notifications,
            })
        return {
            "schema_version": "1.0",
            "agent": "member3_bid_workspace_pipeline",
            "mode": "INPUT_JSON_ORCHESTRATION",
            "assessment_count": len(results),
            "results": results,
            "notifications": all_notifications,
            "human_review_required": True,
            "limitations": [
                "Uses supplied upstream assessment reports and snapshots only.",
                "Snapshot comparison is not live portal monitoring.",
                "Notification objects are payloads only; no email, SMS, or push message is sent.",
                "Scores are readiness indicators, not probabilities of winning or legal determinations.",
            ],
        }


def load_json_list(path: str | Path, key: str | None = None) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as stream:
        data = json.load(stream)
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict) and key and isinstance(data.get(key), list):
        rows = data[key]
    elif isinstance(data, dict) and isinstance(data.get("results"), list):
        rows = data["results"]
    else:
        raise ValueError(f"Expected a JSON list or an object containing list key '{key or 'results'}'.")
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("Each entry in the input list must be a JSON object.")
    return rows
