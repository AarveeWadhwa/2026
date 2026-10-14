"""FastAPI application for the integrated BidPilot AI decision-support workspace."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.agents.tender_intelligence_agent import TenderIntelligenceAgent
from backend.services.tender_assessment_pipeline import TenderAssessmentPipeline
from backend.services.tender_quality import validate_envelope
from backend.services.bid_workspace_pipeline import BidWorkspacePipeline
from backend.services.bid_portfolio_report import BidPortfolioReport
from backend.services.assessment_insights import AssessmentInsights
from backend.services.tender_memory import TenderMemoryStore
from backend.agents.replanning_agent import ReplanningAgent
from backend.services.preference_memory import PreferenceMemory
from backend.services.source_monitor import SourceMonitor
from backend.services.action_register import ActionRegister, AGENTS

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FRONTEND = ROOT / "frontend"
MEMORY = TenderMemoryStore(DATA / "bidpilot_memory.sqlite3")
REPLANNER = ReplanningAgent()
PREFERENCES = PreferenceMemory(DATA / "bidpilot_memory.sqlite3")
SOURCE_MONITOR = SourceMonitor(DATA / "bidpilot_memory.sqlite3", DATA / "monitor_sources.json")
ACTIONS = ActionRegister(DATA / "bidpilot_memory.sqlite3")
app = FastAPI(title="BidPilot AI", version="1.0.0", description="Tender discovery, requirement extraction, eligibility screening, compliance tracking and bid-readiness reporting.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")

class CompanyInput(BaseModel):
    company_name: str = Field(default="Demo IT Solutions", min_length=1, max_length=200)
    industry: str = "IT services"
    services: list[str] = Field(default_factory=lambda: ["computer hardware", "networking", "software support"])
    location: str = "Pune, Maharashtra"
    annual_turnover_inr: float | None = Field(default=14000000, ge=0)
    years_experience: float | None = Field(default=4, ge=0)
    certifications: list[str] = Field(default_factory=lambda: ["ISO 9001", "GST", "PAN"])
    available_documents: list[str] = Field(default_factory=lambda: ["PAN.pdf", "GST Registration Certificate.pdf", "Turnover Certificate.pdf", "Audited Financial Statements.pdf"])
    keywords: list[str] = Field(default_factory=lambda: ["laptop", "network", "software", "cybersecurity"])

class RunRequest(BaseModel):
    company: CompanyInput = Field(default_factory=CompanyInput)
    limit: int = Field(default=10, ge=1, le=50)
    min_score: float = Field(default=0, ge=0, le=100)

class ActionCreateInput(BaseModel):
    company: CompanyInput = Field(default_factory=CompanyInput)
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=2000)
    tender_id: str = Field(default="", max_length=100)
    tender_title: str = Field(default="", max_length=300)
    agent_key: str = Field(default="manual", max_length=80)
    priority: str = "medium"
    status: str = "open"
    assignee: str = Field(default="", max_length=200)
    due_date: str = Field(default="", max_length=30)
    notes: str = Field(default="", max_length=4000)

class ActionUpdateInput(BaseModel):
    company: CompanyInput = Field(default_factory=CompanyInput)
    title: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=2000)
    priority: str | None = None
    status: str | None = None
    assignee: str | None = Field(default=None, max_length=200)
    due_date: str | None = Field(default=None, max_length=30)
    notes: str | None = Field(default=None, max_length=4000)

@app.get("/")
def home():
    return FileResponse(FRONTEND / "index.html")

@app.get("/api/health")
def health():
    return {"status": "ok", "app": "BidPilot AI", "mode": "local_sample_catalogue", "version": "1.0.0"}

@app.get("/api/sample-company")
def sample_company():
    return json.loads((DATA / "sample_company.json").read_text(encoding="utf-8"))

@app.get("/api/tenders")
def list_tenders():
    catalogue = json.loads((DATA / "sample_tenders" / "tenders.json").read_text(encoding="utf-8"))
    items = catalogue if isinstance(catalogue, list) else catalogue.get("tenders", catalogue.get("results", []))
    return {"count": len(items), "mode": "local_catalogue", "results": items}

@app.post("/api/run")
def run_pipeline(request: RunRequest):
    try:
        company = request.company.model_dump()
        # Explicit user feedback adapts discovery keywords across cycles. Base profile
        # values remain intact and negative preferences are not used as hard exclusions.
        learned = PREFERENCES.profile(company)
        base_keywords = list(company.get("keywords") or [])
        company["keywords"] = list(dict.fromkeys(base_keywords + learned["preferred_keywords"]))
        company["deprioritized_keywords"] = learned["deprioritized_keywords"]
        # Load prior company/tender history before running this cycle. Every run re-assesses
        # current tender data; changed monitored fields also generate an explicit replan.
        prior_history = MEMORY.get_company_history(company)
        discovery = TenderIntelligenceAgent().run(company, limit=request.limit, min_score=request.min_score)
        quality = validate_envelope(discovery)
        assessment = TenderAssessmentPipeline().assess(company, discovery)
        assessment_by_id = {str(x.get("tender_id")): x for x in assessment.get("results", [])}
        # Translate Member 2's report contract into the explicit Member 3 contract.
        member3_assessments: list[dict[str, Any]] = []
        snapshots: list[dict[str, Any]] = []
        replanning: list[dict[str, Any]] = []
        for extracted in discovery.get("results", []):
            tid = str(extracted.get("tender_id") or (extracted.get("discovery") or {}).get("tender_id") or "UNKNOWN")
            report = assessment_by_id.get(tid, {})
            member3_assessments.append({
                "tender_id": tid,
                "eligibility_result": report.get("eligibility", {}),
                "compliance_result": report.get("compliance", {}),
                "tender": {"tender_id": tid, "title": (extracted.get("discovery") or {}).get("title", tid),
                           "deadline": (extracted.get("deadlines") or {}).get("bid_submission_deadline") or (extracted.get("discovery") or {}).get("catalogue_deadline"),
                           "organization": (extracted.get("discovery") or {}).get("organization", "")},
            })
            d = extracted.get("discovery") or {}
            normalized = extracted.get("normalized_requirements") or {}
            snapshot = {"tender_id": tid, "title": d.get("title", tid),
                        "deadline": (extracted.get("deadlines") or {}).get("bid_submission_deadline") or d.get("catalogue_deadline"),
                        "emd": normalized.get("emd_inr", next((x.get("value") for x in extracted.get("financial_requirements", []) if str(x.get("type", "")).lower() == "emd"), None)),
                        "documents_required": extracted.get("documents_required", []),
                        "certifications": normalized.get("certifications", extracted.get("certifications", [])),
                        "eligibility": extracted.get("eligibility", {}),
                        "minimum_turnover": normalized.get("minimum_annual_turnover_inr", extracted.get("eligibility", {}).get("minimum_turnover")),
                        "minimum_experience": normalized.get("minimum_experience_months", extracted.get("eligibility", {}).get("minimum_experience")),
                        "technical_requirements": extracted.get("technical_requirements", []),
                        "source_url": d.get("source_url")}
            snapshots.append(snapshot)
            prior = prior_history.get(tid, {})
            replanning.append({"tender_id": tid, **REPLANNER.plan(prior.get("snapshot"), snapshot, prior.get("assessment"))})
        previous_snapshots = [row["snapshot"] for row in prior_history.values()]

        # Execute a bounded, change-triggered feedback loop. When the planner
        # detects a material change against persistent history, actually rerun
        # requirement extraction for affected tenders, then eligibility/compliance,
        # and finally downstream bid analysis/preparation. The cap prevents loops
        # from running indefinitely; human review remains required.
        replanning_execution: list[dict[str, Any]] = []
        changed_ids = {str(item["tender_id"]) for item in replanning if item.get("replan_required")}
        if changed_ids:
            replanning_execution.append({
                "cycle": 1,
                "trigger": "material_tender_snapshot_change",
                "affected_tender_ids": sorted(changed_ids),
                "executed_stages": ["requirement_extraction", "eligibility", "compliance", "bid_analysis", "bid_preparation"],
                "status": "running",
            })
            # Re-run discovery + extraction from the current configured catalogue
            # so requirement extraction is executed again, not merely marked stale.
            refreshed = TenderIntelligenceAgent().run(company, limit=request.limit, min_score=request.min_score)
            refreshed_by_id = {str(x.get("tender_id") or (x.get("discovery") or {}).get("tender_id") or "UNKNOWN"): x
                               for x in refreshed.get("results", [])}
            for index, extraction in enumerate(discovery.get("results", [])):
                tid = str(extraction.get("tender_id") or (extraction.get("discovery") or {}).get("tender_id") or "UNKNOWN")
                if tid in changed_ids and tid in refreshed_by_id:
                    discovery["results"][index] = refreshed_by_id[tid]
            # Re-run eligibility/compliance only for changed tenders, then replace
            # their old reports with the newly executed assessment outputs.
            changed_extractions = [x for x in discovery.get("results", [])
                                   if str(x.get("tender_id") or (x.get("discovery") or {}).get("tender_id") or "UNKNOWN") in changed_ids]
            if changed_extractions:
                rerun_assessment = TenderAssessmentPipeline().assess(company, {"results": changed_extractions})
                rerun_by_id = {str(x.get("tender_id")): x for x in rerun_assessment.get("results", [])}
                assessment["results"] = [rerun_by_id.get(str(x.get("tender_id")), x) for x in assessment.get("results", [])]
                assessment_by_id = {str(x.get("tender_id")): x for x in assessment.get("results", [])}
                for item in member3_assessments:
                    tid = str(item.get("tender_id"))
                    if tid in changed_ids and tid in assessment_by_id:
                        report = assessment_by_id[tid]
                        item["eligibility_result"] = report.get("eligibility", {})
                        item["compliance_result"] = report.get("compliance", {})
                # Re-run downstream bid analysis and preparation for changed tenders.
                changed_assessments = [x for x in member3_assessments if str(x.get("tender_id")) in changed_ids]
                changed_current = [x for x in snapshots if str(x.get("tender_id")) in changed_ids]
                changed_previous = [x for x in previous_snapshots if str(x.get("tender_id")) in changed_ids]
                rerun_workspace = BidWorkspacePipeline().run(changed_assessments, current_snapshots=changed_current,
                                                              previous_snapshots=changed_previous)
                rerun_by_id = {str(x.get("tender_id")): x for x in rerun_workspace.get("results", [])}
                # The main workspace below is run once for the full portfolio; these
                # rerun outputs replace affected rows after that run.
                replanning_execution[-1]["status"] = "completed"
                replanning_execution[-1]["rerun_tender_count"] = len(changed_assessments)
                replanning_execution[-1]["max_cycles"] = 1
            else:
                replanning_execution[-1]["status"] = "blocked_missing_refreshed_extraction"
                rerun_by_id = {}
        else:
            rerun_by_id = {}

        workspace = BidWorkspacePipeline().run(member3_assessments, current_snapshots=snapshots, previous_snapshots=previous_snapshots)
        if rerun_by_id:
            workspace["results"] = [rerun_by_id.get(str(row.get("tender_id")), row) for row in workspace.get("results", [])]
        workspace["replanning_execution"] = replanning_execution
        portfolio = BidPortfolioReport().build(workspace)
        assessment_insights = AssessmentInsights().build(assessment)
        assessment_by_id_for_memory = {str(x.get("tender_id")): x for x in assessment.get("results", [])}
        memory_updates = []
        for snapshot in snapshots:
            tid = str(snapshot["tender_id"])
            saved = MEMORY.record_cycle(company, tid, snapshot, assessment_by_id_for_memory.get(tid, {}))
            memory_updates.append(saved)
        replan_by_id = {x["tender_id"]: x for x in replanning}
        for result in workspace.get("results", []):
            result["replanning"] = replan_by_id.get(str(result.get("tender_id")), {})
        action_sync = ACTIONS.sync_agent_outputs(company, discovery, assessment, workspace, replanning, replanning_execution)
        action_snapshot = ACTIONS.list(company)
        return {"success": True, "company": {"company_name": company["company_name"]},
                "discovery": discovery, "quality_audit": quality, "assessment": assessment,
                "workspace": workspace, "portfolio": portfolio, "assessment_insights": assessment_insights,
                "replanning": replanning,
                "replanning_execution": replanning_execution,
                "action_register": {**action_sync, "count": action_snapshot["count"], "summary": action_snapshot["summary"]},
                "memory": {"enabled": True, "stored_tender_count": len(MEMORY.get_company_history(company)),
                           "updated_records": memory_updates, "storage": "Supabase PostgreSQL" if __import__("os").getenv("DATABASE_URL") else "local SQLite; scoped by company profile",
                           "learned_preferences": learned},
                "summary": {"tenders_found": discovery.get("result_count", 0),
                            "tenders_assessed": assessment.get("assessed_tender_count", 0),
                            "quality_flags": quality.get("needs_review_count", 0),
                            "actions": sum(len((r.get("analysis") or {}).get("action_items", [])) + len((r.get("preparation_checklist") or {}).get("items", [])) for r in workspace.get("results", [])),
                            "human_review_required": True},
                "limitations": ["Uses fictional/local sample tender records by default; no live portal scraping is configured.",
                                "Extraction is rule-based and must be checked against official tender documents.",
                                "No actual notification is sent. Corrigendum comparison requires previous and current snapshots.",
                                "Eligibility/readiness results are decision support, not legal advice or a guarantee of award."]}
    except (ValueError, TypeError, KeyError, OSError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@app.get("/api/actions")
def list_actions(company_name: str = "Demo IT Solutions", industry: str = "IT services", location: str = "Pune, Maharashtra",
                 status: str = "", tender_id: str = "", agent_key: str = ""):
    if status and status not in {"open", "in_progress", "blocked", "done", "cancelled"}:
        raise HTTPException(status_code=422, detail="Invalid task status")
    if agent_key and agent_key not in AGENTS:
        raise HTTPException(status_code=422, detail="Invalid agent role")
    return ACTIONS.list({"company_name": company_name, "industry": industry, "location": location}, status, tender_id, agent_key)

@app.post("/api/actions")
def create_action(payload: ActionCreateInput):
    try:
        return {"created": True, "task": ACTIONS.create(payload.company.model_dump(), payload.model_dump(exclude={"company"}))}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@app.patch("/api/actions/{task_id}")
def update_action(task_id: str, payload: ActionUpdateInput):
    changes = payload.model_dump(exclude={"company"}, exclude_unset=True)
    changes = {k: v for k, v in changes.items() if v is not None}
    try:
        task = ACTIONS.update(payload.company.model_dump(), task_id, changes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not task:
        raise HTTPException(status_code=404, detail="Task not found for this company profile")
    return {"updated": True, "task": task}

@app.get("/api/actions/{task_id}/history")
def action_history(task_id: str, company_name: str = "Demo IT Solutions", industry: str = "IT services", location: str = "Pune, Maharashtra"):
    task = ACTIONS.get_one({"company_name": company_name, "industry": industry, "location": location}, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found for this company profile")
    return {"task_id": task_id, "events": ACTIONS.events({"company_name": company_name, "industry": industry, "location": location}, task_id)}

@app.get("/api/memory")
def memory_summary(company_name: str = "Demo IT Solutions", industry: str = "IT services", location: str = "Pune, Maharashtra"):
    profile = {"company_name": company_name, "industry": industry, "location": location}
    history = MEMORY.get_company_history(profile)
    return {"enabled": True, "tender_count": len(history),
            "records": [{"tender_id": tid, "cycle_count": item["cycle_count"],
                         "first_seen_at": item["first_seen_at"], "last_seen_at": item["last_seen_at"]}
                        for tid, item in sorted(history.items())]}

@app.delete("/api/memory")
def clear_memory(company_name: str = "Demo IT Solutions", industry: str = "IT services", location: str = "Pune, Maharashtra"):
    profile = {"company_name": company_name, "industry": industry, "location": location}
    return {"deleted_records": MEMORY.clear_company(profile), "cleared": True}

@app.post("/api/audit")
def audit_payload(payload: dict[str, Any]):
    try:
        return validate_envelope(payload)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


class FeedbackInput(BaseModel):
    company: CompanyInput = Field(default_factory=CompanyInput)
    category: str = Field(default="general", max_length=100)
    keywords: list[str] = Field(default_factory=list)
    rating: int = Field(ge=-1, le=1)
    tender_id: str = Field(default="", max_length=100)
    note: str = Field(default="", max_length=500)

@app.get("/api/preferences")
def get_preferences(company_name: str = "Demo IT Solutions", industry: str = "IT services", location: str = "Pune, Maharashtra"):
    return PREFERENCES.profile({"company_name": company_name, "industry": industry, "location": location})

@app.post("/api/preferences/feedback")
def save_preference_feedback(payload: FeedbackInput):
    if payload.rating not in (-1, 1):
        raise HTTPException(status_code=422, detail="rating must be 1 (useful) or -1 (not useful)")
    try:
        company = payload.company.model_dump()
        record = PREFERENCES.record(company, payload.category, payload.keywords, payload.rating, payload.tender_id, payload.note)
        return {"saved": True, "feedback": record, "preferences": PREFERENCES.profile(company)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@app.get("/api/monitor/status")
def monitor_status():
    return SOURCE_MONITOR.status()

@app.post("/api/monitor/run")
def run_source_monitor():
    return SOURCE_MONITOR.run_once()
