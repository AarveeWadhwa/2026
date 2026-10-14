"""Create a human-readable portfolio report from Member 3 bid-workspace JSON.

This module summarizes supplied analysis results. It does not independently verify
eligibility, predict award probability, monitor portals, or send notifications.
"""
from __future__ import annotations
import csv
import json
from pathlib import Path
from typing import Any


def _number(value: Any) -> float | None:
    try:
        if value is None or isinstance(value, bool):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _first(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if mapping.get(key) is not None:
            return mapping[key]
    return None


class BidPortfolioReport:
    """Convert a Member 3 workspace result into a compact bid action register."""

    def build(self, workspace: dict[str, Any]) -> dict[str, Any]:
        raw_results = workspace.get("results", [])
        if not isinstance(raw_results, list):
            raise ValueError("workspace.results must be a list")
        rows: list[dict[str, Any]] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            analysis = item.get("analysis") or {}
            checklist = item.get("preparation_checklist") or {}
            if isinstance(checklist, dict):
                checklist_items = checklist.get("items") or checklist.get("checklist") or []
            elif isinstance(checklist, list):
                checklist_items = checklist
            else:
                checklist_items = []
            missing_docs = []
            for task in checklist_items if isinstance(checklist_items, list) else []:
                if not isinstance(task, dict):
                    continue
                status = str(_first(task, "status", "state") or "").upper()
                label = _first(task, "document", "required_document", "task", "item", "title")
                if label and status in {"MISSING", "BLOCKED", "PENDING", "NOT_STARTED", "INCOMPLETE"}:
                    missing_docs.append(str(label))
            change_report = item.get("change_report") or {}
            changes = change_report.get("changes", []) if isinstance(change_report, dict) else []
            if not isinstance(changes, list):
                changes = []
            score = _number(_first(analysis, "readiness_score", "bid_readiness_score", "score"))
            recommendation = str(_first(analysis, "recommendation", "bid_recommendation", "decision") or "REVIEW")
            risk = str(_first(analysis, "risk_level", "risk", "overall_risk") or "UNKNOWN")
            flags = []
            if missing_docs:
                flags.append(f"{len(missing_docs)} preparation item(s) need attention")
            if changes:
                flags.append(f"{len(changes)} tender change(s) detected")
            if item.get("change_report") is None:
                flags.append("No previous/current snapshot comparison available")
            if analysis.get("human_review_required", True):
                flags.append("Human review required")
            rows.append({
                "tender_id": str(item.get("tender_id") or analysis.get("tender_id") or "UNKNOWN"),
                "title": str(_first(analysis, "tender_title", "title") or ""),
                "recommendation": recommendation,
                "risk_level": risk,
                "readiness_score": score,
                "deadline": str(_first(analysis, "deadline", "bid_submission_deadline") or ""),
                "change_count": len(changes),
                "action_count": len(missing_docs),
                "actions": missing_docs,
                "review_flags": flags,
            })
        rows.sort(key=lambda row: (
            0 if any("deadline" in flag.lower() for flag in row["review_flags"]) else 1,
            row["readiness_score"] if row["readiness_score"] is not None else -1,
            row["tender_id"],
        ), reverse=False)
        recommendations: dict[str, int] = {}
        risks: dict[str, int] = {}
        for row in rows:
            recommendations[row["recommendation"]] = recommendations.get(row["recommendation"], 0) + 1
            risks[row["risk_level"]] = risks.get(row["risk_level"], 0) + 1
        return {
            "schema_version": "1.0",
            "agent": "member3_bid_portfolio_report",
            "source_agent": workspace.get("agent", "unknown"),
            "tender_count": len(rows),
            "recommendation_counts": recommendations,
            "risk_counts": risks,
            "action_register": rows,
            "human_review_required": True,
            "limitations": [
                "This report summarizes supplied workspace output and does not validate source facts.",
                "Missing actions are detected only when checklist items expose a recognized status and label.",
                "Readiness scores are indicators, not probabilities of winning or legal determinations.",
            ],
        }

    @staticmethod
    def write_csv(report: dict[str, Any], path: str | Path) -> None:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        columns = ["tender_id", "title", "recommendation", "risk_level", "readiness_score", "deadline", "change_count", "action_count", "actions", "review_flags"]
        with output.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            for row in report.get("action_register", []):
                writer.writerow({**row, "actions": "; ".join(row.get("actions", [])), "review_flags": "; ".join(row.get("review_flags", []))})

    @staticmethod
    def write_markdown(report: dict[str, Any], path: str | Path) -> None:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        lines = ["# Bid Portfolio Summary", "", f"- Tenders assessed: **{report.get('tender_count', 0)}**", "- Human review required: **Yes**", "", "## Action register", "", "| Tender ID | Recommendation | Risk | Readiness score | Deadline | Actions | Changes |", "|---|---|---|---:|---|---:|---:|"]
        for row in report.get("action_register", []):
            score = row.get("readiness_score")
            score_text = "Not supplied" if score is None else str(score)
            cells = [row.get("tender_id", ""), row.get("recommendation", "REVIEW"), row.get("risk_level", "UNKNOWN"), score_text, row.get("deadline", ""), row.get("action_count", 0), row.get("change_count", 0)]
            lines.append("| " + " | ".join(str(cell).replace("|", "\\|").replace("\n", " ") for cell in cells) + " |")
        lines.extend(["", "## Review flags", ""])
        any_flags = False
        for row in report.get("action_register", []):
            for flag in row.get("review_flags", []):
                lines.append(f"- **{row.get('tender_id', 'UNKNOWN')}:** {flag}")
                any_flags = True
        if not any_flags:
            lines.append("- No flags were emitted by the report generator; manually verify source documents and deadlines.")
        lines.extend(["", "## Limitations", ""])
        lines.extend(f"- {lim}" for lim in report.get("limitations", []))
        output.write_text("\n".join(lines) + "\n", encoding="utf-8")
